import { useNavigate, useLocation } from 'react-router-dom'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { dummySessions, fmtDuration } from '../dummy.js'

/* 세션 리포트 — 운동 종료 직후 요약.
   LiveExercise 에서 { session, report } 를 state 로 받는다.
   직접(기록 탭) 진입 시엔 더미 최근 세션으로 폴백.
   report 본문은 계약③ FeedbackMessage[] (FeedbackCard 재사용). */
export default function SessionReport() {
  const navigate = useNavigate()
  const location = useLocation()

  const fallback = dummySessions[dummySessions.length - 1]
  const session = location.state?.session ?? fallback
  const report = location.state?.report ?? fallback.report

  const durationSec = session.duration_s ?? 0
  const repCount = session.rep_count ?? 0

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">세션 리포트</p>
        <h2 className="title">오늘 운동 정리했어요</h2>

        {/* 세션 메타 */}
        <div className="session-meta">
          <div className="session-meta__item">
            <div className="session-meta__value">{fmtDuration(durationSec)}</div>
            <div className="session-meta__label">운동 시간</div>
          </div>
          <div className="session-meta__item">
            <div className="session-meta__value">{repCount}</div>
            <div className="session-meta__label">횟수</div>
          </div>
          <div className="session-meta__item">
            <div className="session-meta__value">{report.length}</div>
            <div className="session-meta__label">피드백</div>
          </div>
        </div>

        <p className="report-section-title">이번 세션에서 관찰된 패턴</p>
        {report.length === 0 ? (
          <div className="detail-empty">
            이번 세션에서는 특별히 관찰된 패턴이 없었어요.
          </div>
        ) : (
          report.map((m, i) => <FeedbackCard key={i} msg={m} />)
        )}
      </div>

      <div className="screen__footer">
        <button
          className="btn btn--primary"
          onClick={() => navigate('/app/records')}
        >
          기록에서 보기
        </button>
        <button
          className="btn btn--ghost"
          style={{ marginTop: 10 }}
          onClick={() => navigate('/app/exercise')}
        >
          운동 홈으로
        </button>
      </div>
    </div>
  )
}
