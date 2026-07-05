import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { exercise } from '../dummy.js'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { usePoseCamera } from '../hooks/usePoseCamera.js'
import { getDeviceId } from '../state/storage.js'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'
import { fetchSessions } from '../api/sessions.js'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
const WS_BASE_URL = API_BASE_URL.replace(/^http/, 'ws')

// 로컬 날짜를 YYYY-MM-DD 로 (기록 조회용, UTC 밀림 방지)
function todayLocal() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

/* 실시간 운동 — 타이머 / 일시정지 / 피드백 스트림 / 종료 팝업.
   카메라(usePoseCamera)로 뽑은 랜드마크를 WebSocket(/ws/exercise)으로 보내고,
   5~10초 윈도우가 완성될 때마다 서버가 보내주는 피드백을 이 자리에 흘려보낸다. */
export default function LiveExercise() {
  const navigate = useNavigate()
  const profile = useProfileOrFallback()
  const { videoRef, canvasRef, landmarks, confidence, status } = usePoseCamera()
  const [elapsed, setElapsed] = useState(0) // 초
  const [paused, setPaused] = useState(false)
  const [showEnd, setShowEnd] = useState(false)
  // 지금까지 도착한 FeedbackMessage 들 (최신이 위로)
  const [messages, setMessages] = useState([])

  const [sessionId, setSessionId] = useState(null)
  const [wsStatus, setWsStatus] = useState('connecting') // 'connecting' | 'ready' | 'error'
  const [wsError, setWsError] = useState(null)
  const [endingReport, setEndingReport] = useState(false)

  const wsRef = useRef(null)
  const closingRef = useRef(false) // endSession에서 정상 종료 중임을 표시
  const didInitRef = useRef(false) // StrictMode 이중 마운트에서 세션 시작 로직이 두 번 실행되는 것을 방지

  // 1초마다 타이머 (일시정지/팝업 중엔 멈춤)
  useEffect(() => {
    if (paused || showEnd) return
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [paused, showEnd])

  // 세션 시작 -> WebSocket 연결 (최초 1회)
  useEffect(() => {
    if (didInitRef.current) return
    didInitRef.current = true

    let cancelled = false

    async function connect() {
      let newSessionId = null
      try {
        const res = await fetch(`${API_BASE_URL}/session/start`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: getDeviceId(), exercise: exercise.id }),
        })
        if (!res.ok) {
          const body = await res.json().catch(() => null)
          throw new Error(body?.detail ?? `세션 시작 실패 (${res.status})`)
        }
        const data = await res.json()
        newSessionId = data.session_id
      } catch (err) {
        if (cancelled) return
        setWsStatus('error')
        setWsError(err instanceof Error ? err.message : String(err))
        return
      }

      if (cancelled) return
      setSessionId(newSessionId)

      const ws = new WebSocket(
        `${WS_BASE_URL}/ws/exercise?session_id=${newSessionId}&exercise=${exercise.id}`,
      )
      wsRef.current = ws

      ws.onopen = () => {
        if (cancelled) return
        ws.send(JSON.stringify({ type: 'init', profile }))
        setWsStatus('ready')
      }

      ws.onmessage = (event) => {
        if (cancelled) return
        const data = JSON.parse(event.data)
        if (data.window_ready) {
          setMessages((prev) => [...data.messages, ...prev])
        } else if (data.error) {
          setWsError(data.error)
        }
      }

      ws.onerror = () => {
        if (cancelled || closingRef.current) return
        setWsStatus('error')
        setWsError('WebSocket 연결에 오류가 발생했어요.')
      }

      ws.onclose = () => {
        if (cancelled || closingRef.current) return
        setWsStatus('error')
        setWsError('서버와의 연결이 끊어졌어요.')
      }
    }

    connect()

    return () => {
      cancelled = true
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.close()
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 프레임 전송: landmarks가 갱신될 때마다 서버로 전달
  useEffect(() => {
    if (paused || wsStatus !== 'ready') return
    if (landmarks == null) return
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(
        JSON.stringify({
          type: 'frame',
          landmarks,
          timestamp_s: performance.now() / 1000,
        }),
      )
    }
  }, [landmarks, paused, wsStatus])

  const mmss = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(
    elapsed % 60,
  ).padStart(2, '0')}`

  const endSession = async () => {
    if (endingReport) return
    setEndingReport(true)

    closingRef.current = true

    if (wsRef.current) {
      wsRef.current.close()
    }

    // 이번 세션에서 모인 계약③ FeedbackMessage 들(최신이 위라 시간순으로 뒤집음)
    const report = [...messages].reverse()

    let session = null
    try {
      if (sessionId) {
        await fetch(`${API_BASE_URL}/session/end/${sessionId}`, { method: 'POST' })
      }
    } catch {
      // 세션 종료 저장 실패해도 리포트 화면까지는 진행한다
    }

    try {
      const today = todayLocal()
      const sessions = await fetchSessions(getDeviceId(), today, today)
      session = sessions.find((s) => s.session_id === sessionId) ?? null
    } catch {
      session = null
    }

    if (!session) {
      session = {
        session_id: sessionId,
        duration_s: elapsed,
        rep_count: 0,
        date: todayLocal(),
      }
    }

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

      <div className="live__stage" style={{ position: 'relative' }}>
        {paused && <span className="live__paused-badge">일시정지됨</span>}
        <video
          ref={videoRef}
          muted
          playsInline
          autoPlay
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            transform: 'scaleX(-1)',
          }}
        />
        <canvas
          ref={canvasRef}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            transform: 'scaleX(-1)',
          }}
        />
      </div>
      {wsStatus === 'error' && (
        <p className="text-muted" style={{ margin: 0 }}>
          연결에 문제가 있어요: {wsError}
        </p>
      )}

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
              <button
                className="btn btn--primary"
                onClick={endSession}
                disabled={endingReport}
              >
                {endingReport ? '처리 중...' : '종료하고 리포트 보기'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
