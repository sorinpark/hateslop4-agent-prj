import { useNavigate, useLocation } from 'react-router-dom'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { fmtDuration } from '../dummy.js'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'

/* 세션 리포트 — 운동 종료 직후 요약.
   LiveExercise 에서 { session, report } 를 state 로 받는다.
   직접(기록 탭) 진입 시엔 더미 최근 세션으로 폴백.
   report 본문은 계약③ FeedbackMessage[] (FeedbackCard 재사용). */
export default function SessionReport() {
  const navigate = useNavigate()
  const location = useLocation()

  const profile = useProfileOrFallback()

  // 운동 종료 직후 LiveExercise 에서 전달된 세션/리포트
  const session = location.state?.session ?? null
  const report = location.state?.report ?? []

  const durationSec = session?.duration_s ?? 0
  const repCount = session?.rep_count ?? 0
  const focusNames = profile.focus_areas.map((fa) => fa.area).join(', ')

  // 새로고침 등으로 세션 정보 없이 진입한 경우 안내
  if (!session) {
    return (
      <div className="screen">
        <div className="screen__scroll">
          <p className="eyebrow">세션 리포트</p>
          <h2 className="title">표시할 세션이 없어요</h2>
          <div className="detail-empty">
            리포트는 운동을 마친 직후에 보여요. 지난 기록은 기록 탭에서 날짜로
            확인할 수 있어요.
          </div>
        </div>
        <div className="screen__footer">
          <button
            className="btn btn--primary"
            onClick={() => navigate('/app/records')}
          >
            기록 보기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">세션 리포트</p>
        <h2 className="title">오늘 운동 정리했어요</h2>
        <p className="subtitle">관찰 기준: {focusNames}</p>

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
