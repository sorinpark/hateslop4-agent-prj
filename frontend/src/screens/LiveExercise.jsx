import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { dummyFeedbackStream, exercise } from '../dummy.js'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { useSessions } from '../state/SessionContext.jsx'

/* 실시간 운동 — 타이머 / 일시정지 / 피드백 스트림 / 종료 팝업.
   피드백은 schemas.FeedbackResponse 더미를 5~10초 윈도우처럼 순차 표시.
   실제로는 vision -> POST /feedback -> 응답을 이 자리에 흘려보낸다. */
export default function LiveExercise() {
  const navigate = useNavigate()
  const { addSession } = useSessions()
  const [elapsed, setElapsed] = useState(0) // 초
  const [paused, setPaused] = useState(false)
  const [showEnd, setShowEnd] = useState(false)
  // 지금까지 도착한 FeedbackMessage 들 (최신이 위로)
  const [messages, setMessages] = useState([])
  const nextIdx = useRef(0)

  // 1초마다 타이머 (일시정지/팝업 중엔 멈춤)
  useEffect(() => {
    if (paused || showEnd) return
    const id = setInterval(() => setElapsed((s) => s + 1), 1000)
    return () => clearInterval(id)
  }, [paused, showEnd])

  // 더미 피드백 도착: window_end_s 시점이 되면 해당 응답을 펼쳐 넣는다
  useEffect(() => {
    const next = dummyFeedbackStream[nextIdx.current]
    if (next && elapsed >= next.window_end_s) {
      setMessages((prev) => [
        ...next.messages.map((m) => ({ ...m, _w: next.window_end_s })),
        ...prev,
      ])
      nextIdx.current += 1
    }
  }, [elapsed])

  const mmss = `${String(Math.floor(elapsed / 60)).padStart(2, '0')}:${String(
    elapsed % 60,
  ).padStart(2, '0')}`

  const endSession = () => {
    // 이번 세션에서 모인 계약③ FeedbackMessage 들(최신이 위라 시간순으로 뒤집음)
    const report = [...messages].reverse()
    // rep_count 는 vision(MediaPipe) 연동 전이라 경과 시간 기반 추정(약 4초/회).
    // 연동되면 실제 카운트로 교체.
    const repCount = Math.floor(elapsed / 4)
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
        {paused && <span className="live__paused-badge">일시정지됨</span>}
        (실시간 영상 + 스켈레톤 자리)
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
