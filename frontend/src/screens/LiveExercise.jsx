import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { usePoseCamera } from '../hooks/usePoseCamera.js'
import { getDeviceId } from '../state/storage.js'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'
import { fetchSessions } from '../api/sessions.js'
import { useExercise } from '../state/ExerciseContext.jsx'

const POPUP_DURATION_MS = 5000 // 팝업 노출 시간(4~5초 범위 중 5초로 시작)

// 두 피드백 메시지가 "같은 내용"인지: area 일치 + evidence 키 대분류(prefix)가 겹치면 같은 내용으로 본다.
// (LLM이 매번 다른 문장을 생성해서 텍스트 완전일치로는 못 묶으므로 구조화된 필드로 판정)
function isSimilarFeedback(a, b) {
  if (a.area !== b.area) return false
  const prefixes = (m) => new Set((m.evidence ?? []).map((e) => e.split('.')[0]))
  const pa = prefixes(a)
  for (const p of prefixes(b)) {
    if (pa.has(p)) return true
  }
  return false
}

// 3n번째 rep 시점에 팝업으로 띄울 메시지 하나를 고른다.
// buffer: 직전 트리거 이후 도착한 메시지들 / fallbackList: 세션 전체 이력(최신이 앞)
function pickPopupCandidate(buffer, fallbackList) {
  const candidates = buffer.filter((m) => m.type === 'suggestion')
  if (candidates.length === 1) return candidates[0]
  if (candidates.length > 1) {
    for (let i = candidates.length - 1; i > 0; i--) {
      for (let j = i - 1; j >= 0; j--) {
        if (isSimilarFeedback(candidates[i], candidates[j])) return candidates[i]
      }
    }
    return candidates[candidates.length - 1] // 겹치는 게 없으면 구간 내 최신 것
  }
  return fallbackList[0] ?? null // 구간에 popup 후보가 아예 없으면 전체 이력 중 최신 것
}

// 3rep 구간에 모인 메시지들을 흡사한 것끼리 묶어 대표 1개씩만 남긴다(총로그탭용).
function dedupeBatch(batch) {
  const kept = []
  for (const msg of batch) {
    if (!kept.some((k) => isSimilarFeedback(k, msg))) {
      kept.push(msg)
    }
  }
  return kept
}

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
  const { exercise } = useExercise()
  const profile = useProfileOrFallback()
  const [elapsed, setElapsed] = useState(0) // 초
  const [paused, setPaused] = useState(false)
  const [showEnd, setShowEnd] = useState(false)
  // 총로그탭: 3rep 구간마다 dedupe된 메시지가 쌓이는 세션 전체 이력 (최신이 위)
  const [logEntries, setLogEntries] = useState([])
  const [showLog, setShowLog] = useState(false)

  // 셋 중 하나라도 켜지면 화면을 얼리고(카메라/인식 정지) 서버 전송도 멈춘다.
  const cameraPaused = paused || showEnd || showLog

  const { videoRef, canvasRef, landmarks, confidence, status, cameraStream } =
    usePoseCamera(cameraPaused)
  const bgVideoRef = useRef(null)
  // 지금까지 도착한 FeedbackMessage 들 (최신이 위로)
  const [messages, setMessages] = useState([])
  const messagesRef = useRef([]) // WS 콜백에서 최신 messages를 읽기 위한 미러
  useEffect(() => {
    messagesRef.current = messages
  }, [messages])

  // 팝업(행동교정): 3n번째 rep 직후 표시되는 메시지 하나
  const [popup, setPopup] = useState(null)
  const popupTimeoutRef = useRef(null)
  const pendingRef = useRef([]) // 마지막 3n 트리거 이후 도착한 메시지 버퍼
  const totalRepsRef = useRef(0) // 세션 누적 rep (윈도우마다 리셋되는 서버 값과 별개)

  useEffect(() => {
    return () => {
      if (popupTimeoutRef.current) clearTimeout(popupTimeoutRef.current)
    }
  }, [])

  const [sessionId, setSessionId] = useState(null)
  const [wsStatus, setWsStatus] = useState('connecting') // 'connecting' | 'ready' | 'error'
  const [wsError, setWsError] = useState(null)
  const [endingReport, setEndingReport] = useState(false)

  const wsRef = useRef(null)
  useEffect(() => {
    const bgVideo = bgVideoRef.current
    if (!bgVideo || !cameraStream) return

    bgVideo.srcObject = cameraStream
    bgVideo.play().catch(() => {})
  }, [cameraStream])

  // usePoseCamera의 메인 video와 마찬가지로, 배경 video도 같이 얼려야 화면
  // 전체가 정지한 것처럼 보인다(안 그러면 배경만 계속 살아 움직임).
  useEffect(() => {
    const bgVideo = bgVideoRef.current
    if (!bgVideo) return
    if (cameraPaused) {
      bgVideo.pause()
    } else {
      bgVideo.play().catch(() => {})
    }
  }, [cameraPaused])
  const closingRef = useRef(false) // endSession에서 정상 종료 중임을 표시

  // 1초마다 타이머 (일시정지/종료확인/상세로그 중엔 멈춤)
  useEffect(() => {
    if (cameraPaused) return
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [cameraPaused])

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
          body: JSON.stringify({ user_id: getDeviceId(), exercise: exercise.slug }),
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
        `${WS_BASE_URL}/ws/exercise?session_id=${newSessionId}&exercise=${exercise.slug}`,
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
          pendingRef.current = [...pendingRef.current, ...data.messages]

          if (typeof data.rep_count === 'number' && data.rep_count > 0) {
            const prevTotal = totalRepsRef.current
            const nextTotal = prevTotal + data.rep_count
            totalRepsRef.current = nextTotal

            // 누적 rep이 3의 배수 경계를 넘었으면 팝업 트리거 + 총로그탭에 dedupe해서 기록
            if (Math.floor(prevTotal / 3) !== Math.floor(nextTotal / 3)) {
              const batch = pendingRef.current
              const chosen = pickPopupCandidate(batch, messagesRef.current)
              const deduped = dedupeBatch(batch)
              pendingRef.current = []

              if (deduped.length > 0) {
                setLogEntries((prev) => [...deduped, ...prev])
              }
              if (chosen) {
                if (popupTimeoutRef.current) clearTimeout(popupTimeoutRef.current)
                setPopup({ ...chosen, _popupKey: Date.now() })
                popupTimeoutRef.current = setTimeout(() => setPopup(null), POPUP_DURATION_MS)
              }
            }
          }
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
  const MIN_SEND_INTERVAL_MS = 80 // 약 12fps
  const MAX_BUFFERED_BYTES = 200 * 1024 // 송신 버퍼가 이보다 밀리면 프레임 드롭
  useEffect(() => {
    // 일시정지/종료확인/상세로그 중 어느 것이든 켜져 있으면 전송을 막는다 —
    // 예전엔 paused/showEnd만 봐서, 상세로그를 보는 동안엔 계속 전송되고 있었다.
    if (cameraPaused || wsStatus !== 'ready') return
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
      // 예전엔 화면에 보이는 진단 오버레이였던 정보 — 마무리 단계에서 오버레이는 지우고
      // 디버깅용으로 console.log만 남긴다(10프레임마다, 과도한 로그 방지).
      if (sentFramesRef.current % 10 === 0) {
        console.log(
          `[live] WS:${wsStatus} 전송:${sentFramesRef.current} 관절:${landmarks ? 'O' : 'X'} ` +
            `신뢰도:${confidence == null ? '-' : Math.round(confidence * 100) + '%'} 카메라:${status}`,
        )
      }
    }
    // confidence/status는 로그 출력에만 쓰고, 그것 때문에 이 effect가 다시 돌 필요는
    // 없다(전송 타이밍은 landmarks 갱신에만 반응하면 충분) — 그래서 deps에서 뺀다.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [landmarks, cameraPaused, wsStatus])

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
      state: { session, report, from: 'live' },
    })
  }

  return (
    <div className="live">
      <div className="live__top">
        <span className="live__timer">{mmss}</span>
        <span className="live__reps">{exercise.name} · {messages.length}개 피드백</span>
      </div>

      <div className="live__stage" style={{ position: 'relative' }}>
        {/* showEnd(종료 확인 팝업)도 일시정지와 동일한 배지로 보여준다 */}
        {(paused || showEnd) && <span className="live__paused-badge">일시정지됨</span>}
        <video
          ref={bgVideoRef}
          className="camera-video-bg"
          muted
          playsInline
          autoPlay
          aria-hidden="true"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
          }}
        />
        <video
          ref={videoRef}
          className="camera-video-main"
          muted
          playsInline
          autoPlay
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            transform: 'scaleX(-1)', // 전면 카메라 거울 모드 (CameraGuard와 통일)
          }}
        />
        <canvas
          ref={canvasRef}
          className="camera-overlay-main"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            transform: 'scaleX(-1)', // video와 동일하게 반전(스켈레톤 정렬 유지)
          }}
        />

        {/* 팝업(행동교정): 3n번째 rep 직후 상단에 잠깐 떴다 fade-out.
            상시 노출 대신 트리거 시점에만 하나씩 보여줘서 로그 과다 노출을 줄인다.
            전체 목록(총로그탭)은 별도로 제공된다. */}
        {popup && (
          <div className="fb-popup" key={popup._popupKey}>
            <FeedbackCard msg={popup} />
          </div>
        )}

        {/* 총로그탭 진입 버튼: 카메라 화면 우측 하단 */}
        <button
          type="button"
          className="log-toggle-btn"
          onClick={() => setShowLog(true)}
        >
          상세 로그
        </button>
      </div>

      {/* 총로그탭: 팝업 내용 + 상세 관측 전체(3rep 단위 dedupe) — 반투명 오버레이,
          뒤 운동화면이 비치도록 배경은 blur + 반투명만 준다. */}
      {showLog && (
        <div className="log-overlay" onClick={() => setShowLog(false)}>
          <div className="log-overlay__panel" onClick={(e) => e.stopPropagation()}>
            <div className="log-overlay__head">
              <h3>상세 로그</h3>
              <button
                type="button"
                className="log-overlay__close"
                aria-label="닫기"
                onClick={() => setShowLog(false)}
              >
                ×
              </button>
            </div>
            <div className="log-overlay__list">
              {logEntries.length === 0 ? (
                <p className="fb__empty">아직 기록된 피드백이 없어요.</p>
              ) : (
                logEntries.map((m, i) => (
                  <FeedbackCard key={logEntries.length - i} msg={m} />
                ))
              )}
            </div>
          </div>
        </div>
      )}
      {wsStatus === 'error' && (
        <p className="text-muted" style={{ margin: 0 }}>
          연결에 문제가 있어요: {wsError}
        </p>
      )}

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
