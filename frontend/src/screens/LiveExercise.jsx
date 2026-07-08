import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { exercise } from '../dummy.js'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { usePoseCamera } from '../hooks/usePoseCamera.js'
import { getDeviceId } from '../state/storage.js'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'
import { fetchSessions } from '../api/sessions.js'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL
// API_BASE_URL이 있으면 그걸 ws(s)로 바꿔 쓰고, 비어 있으면(=Vite 프록시 사용)
// 현재 페이지 origin에서 ws/wss를 유도한다. https 페이지(폰)면 wss로 맞춰진다.
const WS_BASE_URL = API_BASE_URL
  ? API_BASE_URL.replace(/^http/, 'ws')
  : `${window.location.protocol === 'https:' ? 'wss' : 'ws'}://${window.location.host}`

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

  // 1초마다 타이머 (일시정지/팝업 중엔 멈춤)
  useEffect(() => {
    if (paused || showEnd) return
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [paused, showEnd])

  // 세션 시작 -> WebSocket 연결.
  // StrictMode(dev)는 이 effect를 [마운트→언마운트→재마운트]로 두 번 돌린다.
  // 예전 코드는 didInitRef 가드로 재실행을 막았는데, 그러면 1차 실행이 cleanup의
  // cancelled=true로 무효화된 뒤 2차 실행이 아예 안 일어나 영원히 'connecting'에
  // 멈추는 버그가 있었다(특히 폰: /session/start가 느려 그 사이 언마운트가 확실히
  // 일어남). 그래서 가드를 없애고, 매 실행이 자기 WS를 만들고 cleanup에서 그 WS를
  // 확실히 닫도록 한다. 이 effect 인스턴스에 종속된 로컬 변수(myWs, cancelled)만 본다.
  useEffect(() => {
    let cancelled = false
    let myWs = null

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
      myWs = ws
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
      // 이 실행이 만든 WS를 상태와 무관하게 닫는다(CONNECTING 중이어도 close 가능).
      if (myWs) {
        try {
          myWs.close()
        } catch {
          // 이미 닫혔거나 초기 상태면 무시
        }
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 프레임 전송: landmarks가 갱신될 때마다 서버로 전달.
  // 단, 30fps 전량을 터널로 보내면(초당 30 x 33랜드마크 JSON) 트래픽이 커서
  // 연결이 끊길 수 있다. 서버는 5초 윈도우로 모으니 초당 ~12프레임이면 충분하다.
  // (1) 최소 전송 간격으로 스로틀 + (2) WS 송신 버퍼가 밀리면 그 프레임은 건너뛴다.
  const sentFramesRef = useRef(0)
  const lastSentAtRef = useRef(0)
  const [sentFrames, setSentFrames] = useState(0) // 진단 표시용
  const MIN_SEND_INTERVAL_MS = 80 // 약 12fps
  const MAX_BUFFERED_BYTES = 200 * 1024 // 송신 버퍼가 이보다 밀리면 프레임 드롭
  useEffect(() => {
    if (paused || wsStatus !== 'ready') return
    if (landmarks == null) return
    const now = performance.now()
    if (now - lastSentAtRef.current < MIN_SEND_INTERVAL_MS) return
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      // 백프레셔: 아직 안 나간 데이터가 많으면 이번 프레임은 버린다(최신 우선).
      if (ws.bufferedAmount > MAX_BUFFERED_BYTES) return
      lastSentAtRef.current = now
      ws.send(
        JSON.stringify({
          type: 'frame',
          landmarks,
          timestamp_s: now / 1000,
        }),
      )
      sentFramesRef.current += 1
      // 매 프레임 setState는 과하니 10프레임마다 화면 갱신
      if (sentFramesRef.current % 10 === 0) setSentFrames(sentFramesRef.current)
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
        {/* 임시 진단 오버레이 (원인 파악용) */}
        <div
          style={{
            position: 'absolute',
            top: 6,
            right: 6,
            zIndex: 2,
            fontSize: 11,
            lineHeight: 1.4,
            padding: '4px 8px',
            borderRadius: 6,
            background: 'rgba(0,0,0,0.6)',
            color: '#fff',
            textAlign: 'right',
            pointerEvents: 'none',
          }}
        >
          WS:{wsStatus} · 전송:{sentFrames}
          <br />
          관절:{landmarks ? 'O' : 'X'} · 신뢰도:
          {confidence == null ? '-' : Math.round(confidence * 100) + '%'}
          <br />
          카메라:{status}
        </div>
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
            transform: 'scaleX(-1)', // 거울 모드(전면 카메라처럼 좌우 반전)
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
            transform: 'scaleX(-1)', // video와 동일하게 반전(스켈레톤 정렬 유지)
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
