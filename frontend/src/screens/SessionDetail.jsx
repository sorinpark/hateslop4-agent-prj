import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import FeedbackCard from '../components/FeedbackCard.jsx'
import { fmtDuration, fmtTime } from '../dummy.js'
import { fetchSessions, fetchSessionFeedback } from '../api/sessions.js'
import { getDeviceId } from '../state/storage.js'

/* 날짜별 피드백 상세 — 캘린더/리스트에서 선택한 날짜의 세션 리포트.
   URL: /app/records/:date (YYYY-MM-DD)
   하루에 세션이 여러 개일 수 있어 전부 조회해서 세션별로 반복 렌더링한다.
   report 본문은 계약③ FeedbackMessage[] (FeedbackCard 재사용). */
export default function SessionDetail() {
  const navigate = useNavigate()
  const { date } = useParams()
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchSessions(getDeviceId(), date, date)
      .then(async (list) => {
        const finished = list.filter((s) => s.duration_s != null)
        const withReports = await Promise.all(
          finished.map(async (session) => ({
            ...session,
            report: await fetchSessionFeedback(session.session_id),
          })),
        )
        if (cancelled) return
        setSessions(withReports)
      })
      .catch((err) => {
        if (cancelled) return
        setError(err.message)
      })
      .finally(() => {
        if (cancelled) return
        setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [date])

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

        {loading ? (
          <p className="text-muted">불러오는 중...</p>
        ) : error ? (
          <p className="text-muted">{error}</p>
        ) : sessions.length === 0 ? (
          <>
            <h2 className="title">기록이 없어요</h2>
            <div className="detail-empty">이 날짜에는 운동 기록이 없어요.</div>
          </>
        ) : (
          <>
            <h2 className="title">이 날의 패턴</h2>

            {sessions.map((session) => (
              <div key={session.session_id}>
                {sessions.length > 1 && (
                  <p className="text-muted">{fmtTime(session.started_at)}</p>
                )}

                <div className="session-meta">
                  <div className="session-meta__item">
                    <div className="session-meta__value">
                      {fmtDuration(session.duration_s)}
                    </div>
                    <div className="session-meta__label">운동 시간</div>
                  </div>
                  <div className="session-meta__item">
                    <div className="session-meta__value">
                      {session.rep_count}
                    </div>
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
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  )
}
