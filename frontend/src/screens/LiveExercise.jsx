import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { exercise } from '../dummy.js'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { useSessions } from '../state/SessionContext.jsx'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'
import { createPoseLandmarker, toLandmarkPayload } from '../lib/pose.js'
import { API_BASE, WS_BASE } from '../config.js'

const FRAME_INTERVAL_MS = 200 // 5fps로 서버에 전송 (5초 윈도우 집계엔 충분)

/* 실시간 운동 — 타이머 / 일시정지 / 피드백 스트림 / 종료 팝업.
   카메라(getUserMedia) + MediaPipe PoseLandmarker로 프레임마다 랜드마크를 추출해
   POST /session/start로 받은 session_id로 /ws/exercise에 연결해 전송하고,
   5초 윈도우가 찰 때마다 서버가 보내주는 FeedbackResponse를 그대로 쌓아 보여준다. */
export default function LiveExercise() {
  const navigate = useNavigate()
  const { addSession } = useSessions()
  const profile = useProfileOrFallback()
  const [elapsed, setElapsed] = useState(0) // 초
  const [paused, setPaused] = useState(false)
  const [showEnd, setShowEnd] = useState(false)
  // 'connecting' | 'live' | 'error'
  const [phase, setPhase] = useState('connecting')
  // 지금까지 도착한 FeedbackMessage 들 (최신이 위로)
  const [messages, setMessages] = useState([])

  const videoRef = useRef(null)
  const wsRef = useRef(null)
  const landmarkerRef = useRef(null)
  const streamRef = useRef(null)
  const intervalRef = useRef(null)
  const sessionIdRef = useRef(null)
  const activeRef = useRef(true) // 일시정지/종료팝업 중엔 프레임 전송 중단

  useEffect(() => {
    activeRef.current = !paused && !showEnd
  }, [paused, showEnd])

  // 1초마다 타이머 (연결 전/일시정지/팝업 중엔 멈춤)
  useEffect(() => {
    if (phase !== 'live' || paused || showEnd) return
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [phase, paused, showEnd])

  // 세션 시작 -> 카메라/PoseLandmarker 준비 -> WebSocket 연결 -> 프레임 전송 루프
  useEffect(() => {
    let cancelled = false

    async function setup() {
      let sessionId
      try {
        const startResp = await fetch(`${API_BASE}/session/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: profile.user_id, exercise: exercise.id }),
        })
        if (!startResp.ok) throw new Error('session start failed')
        sessionId = (await startResp.json()).session_id
      } catch {
        if (!cancelled) setPhase('error')
        return
      }
      if (cancelled) return
      sessionIdRef.current = sessionId

      let stream
      try {
        stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user' } })
      } catch {
        if (!cancelled) setPhase('error')
        return
      }
      if (cancelled) {
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      streamRef.current = stream
      videoRef.current.srcObject = stream
      await videoRef.current.play()

      let landmarker
      try {
        landmarker = await createPoseLandmarker()
      } catch {
        if (!cancelled) setPhase('error')
        return
      }
      if (cancelled) {
        landmarker.close()
        return
      }
      landmarkerRef.current = landmarker

      const ws = new WebSocket(
        `${WS_BASE}/ws/exercise?session_id=${sessionId}&exercise=${exercise.id}`,
      )
      wsRef.current = ws

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'init', profile }))
      }
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        if (data.window_ready) {
          setMessages((prev) => [...data.messages, ...prev])
        } else if (data.error) {
          console.warn('[ws]', data.error)
        }
      }
      ws.onerror = () => {
        if (!cancelled) setPhase('error')
      }

      const frameLoopStart = performance.now()
      intervalRef.current = setInterval(() => {
        if (!activeRef.current) return
        if (!videoRef.current || !landmarkerRef.current) return
        if (ws.readyState !== WebSocket.OPEN) return
        const result = landmarkerRef.current.detectForVideo(videoRef.current, performance.now())
        const landmarks = result.landmarks?.[0]
        if (!landmarks) return
        ws.send(
          JSON.stringify({
            type: 'frame',
            landmarks: toLandmarkPayload(landmarks),
            timestamp_s: (performance.now() - frameLoopStart) / 1000,
          }),
        )
      }, FRAME_INTERVAL_MS)

      if (!cancelled) setPhase('live')
    }

    setup()

    return () => {
      cancelled = true
      if (intervalRef.current) clearInterval(intervalRef.current)
      wsRef.current?.close()
      landmarkerRef.current?.close()
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const mmss = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(
    elapsed % 60,
  ).padStart(2, '0')}`

  const endSession = async () => {
    // 이번 세션에서 모인 계약③ FeedbackMessage 들(최신이 위라 시간순으로 뒤집음)
    const report = [...messages].reverse()
    // rep_count는 /ws/exercise 응답에 포함되지 않아(FeedbackResponse에 없음)
    // 경과 시간 기반 추정을 그대로 유지(약 4초/회).
    const repCount = Math.floor(elapsed / 4)

    if (intervalRef.current) clearInterval(intervalRef.current)
    wsRef.current?.close()
    landmarkerRef.current?.close()
    streamRef.current?.getTracks().forEach((t) => t.stop())

    const sessionId = sessionIdRef.current
    if (sessionId) {
      try {
        await fetch(`${API_BASE}/session/end/${sessionId}`, { method: 'POST' })
      } catch {
        // 종료 기록 실패해도 로컬 리포트는 그대로 보여준다
      }
    }

    // 실제 기록으로 저장(localStorage) 후, 저장된 세션을 리포트로 전달
    const session = addSession({
      exercise: exercise.id,
      durationSec: elapsed,
      repCount,
      report,
    })
    navigate('/app/records/report', {
      state: { session, report },
    })
  }

  return (
    <div className="live">
      <div className="live__top">
        <span className="live__timer">{mmss}</span>
        <span className="live__reps">스쿼트 · {messages.length}개 피드백</span>
      </div>

      <div className="live__stage">
        <video ref={videoRef} className="live__video" muted playsInline />
        {phase === 'connecting' && (
          <span className="live__paused-badge">카메라/서버 연결 중...</span>
        )}
        {phase === 'error' && (
          <span className="live__paused-badge">
            연결에 실패했어요. 카메라 권한과 서버 상태를 확인해주세요.
          </span>
        )}
        {paused && phase === 'live' && (
          <span className="live__paused-badge">일시정지됨</span>
        )}
      </div>

      {/* 피드백 스트림 */}
      <div className="fb__feed">
        {messages.length === 0 && (
          <p className="fb__empty">
            자세를 잡고 운동을 시작하면 패턴을 관찰해 알려드려요.
          </p>
        )}
        {messages.map((m, i) => (
          <FeedbackCard key={i} msg={m} />
        ))}
      </div>

      <div className="live__actions">
        <button
          className="btn btn--ghost"
          onClick={() => setPaused((p) => !p)}
          disabled={phase !== 'live'}
        >
          {paused ? '재개' : '일시정지'}
        </button>
        <button className="btn btn--primary" onClick={() => setShowEnd(true)}>
          운동 종료
        </button>
      </div>

      {/* 종료 확인 팝업 */}
      {showEnd && (
        <div className="modal-backdrop" onClick={() => setShowEnd(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3 className="modal__title">운동을 종료할까요?</h3>
            <p className="modal__body">
              지금까지의 기록으로 세션 리포트를 만들어요. 종료하면 이어서 진행할
              수 없어요.
            </p>
            <div className="modal__actions">
              <button
                className="btn btn--ghost"
                onClick={() => setShowEnd(false)}
              >
                계속하기
              </button>
              <button className="btn btn--primary" onClick={endSession}>
                종료하고 리포트 보기
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
