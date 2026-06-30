import { useNavigate, useParams } from 'react-router-dom'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { sessionByDate, fmtDuration } from '../dummy.js'

/* 날짜별 피드백 상세 — 캘린더/리스트에서 선택한 날짜의 세션 리포트.
   URL: /app/records/:date (YYYY-MM-DD)
   report 본문은 계약③ FeedbackMessage[] (FeedbackCard 재사용). */
export default function SessionDetail() {
  const navigate = useNavigate()
  const { date } = useParams()
  const session = sessionByDate(date)

  return (
    <div className="screen">
      <div className="screen__scroll">
        <div className="topbar">
          <button
            className="topbar__back"
            onClick={() => navigate('/app/records')}
          >
            ‹
          </button>
          <p className="eyebrow" style={{ margin: 0 }}>
            {date}
          </p>
        </div>

        {!session ? (
          <>
            <h2 className="title">기록이 없어요</h2>
            <div className="detail-empty">이 날짜에는 운동 기록이 없어요.</div>
          </>
        ) : (
          <>
            <h2 className="title">이 날의 패턴</h2>

            <div className="session-meta">
              <div className="session-meta__item">
                <div className="session-meta__value">
                  {fmtDuration(session.duration_s)}
                </div>
                <div className="session-meta__label">운동 시간</div>
              </div>
              <div className="session-meta__item">
                <div className="session-meta__value">{session.rep_count}</div>
                <div className="session-meta__label">횟수</div>
              </div>
              <div className="session-meta__item">
                <div className="session-meta__value">
                  {session.report.length}
                </div>
                <div className="session-meta__label">피드백</div>
              </div>
            </div>

            <p className="report-section-title">관찰된 패턴</p>
            {session.report.map((m, i) => (
              <FeedbackCard key={i} msg={m} />
            ))}
          </>
        )}
      </div>
    </div>
  )
}
