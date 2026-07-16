import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { fmtDuration } from '../dummy.js'
import { fetchSessionReport } from '../api/sessions.js'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'

/* 세션 리포트 — 운동 종료 직후 요약.
   LiveExercise 에서 { session, report } 를 state 로 받는다.
   직접(기록 탭) 진입 시엔 더미 최근 세션으로 폴백.
   본문은 계약④ ReportSummary — 세션 중 쌓인 피드백을 AI가 1회 정리한
   총평 + 빈도별 항목(GET /sessions/{id}/report)으로 보여준다. */
export default function SessionReport() {
  const navigate = useNavigate()
  const location = useLocation()

  const profile = useProfileOrFallback()

  // 운동 종료 직후 LiveExercise 에서 전달된 세션 (report는 더 이상 안 씀 — AI 요약으로 대체)
  const session = location.state?.session ?? null

  const [aiReport, setAiReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!session?.session_id) {
      setLoading(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setError(null)
    fetchSessionReport(session.session_id)
      .then((data) => {
        if (cancelled) return
        setAiReport(data)
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
  }, [session?.session_id])

  const durationSec = session?.duration_s ?? 0
  const repCount = session?.rep_count ?? 0
  const feedbackCount = aiReport?.items.length ?? 0
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
            <div className="session-meta__value">{feedbackCount}</div>
            <div className="session-meta__label">피드백</div>
          </div>
        </div>

        <p className="report-section-title">이번 세션 총평</p>
        {loading ? (
          <p className="text-muted">정리하는 중...</p>
        ) : error ? (
          <p className="text-muted">{error}</p>
        ) : !aiReport ? (
          <div className="detail-empty">
            이번 세션에서는 특별히 관찰된 패턴이 없었어요.
          </div>
        ) : (
          <>
            <div className="report-summary">{aiReport.summary}</div>

            <p className="report-section-title">관찰된 패턴</p>
            {aiReport.items.length === 0 ? (
              <div className="detail-empty">
                이번 세션에서는 특별히 관찰된 패턴이 없었어요.
              </div>
            ) : (
              aiReport.items.map((item, i) => (
                <div className="report-item" key={i}>
                  <span className="report-item__text">{item.text}</span>
                  <span className="report-item__count">{item.count}회</span>
                </div>
              ))
            )}
          </>
        )}
      </div>

      <div className="screen__footer">
        <div className="btn-row">
          <button
            className="btn btn--ghost"
            onClick={() => navigate('/app/exercise')}
          >
            운동 홈으로
          </button>
          <button
            className="btn btn--primary"
            onClick={() => navigate('/app/records')}
          >
            기록에서 보기
          </button>
        </div>
      </div>
    </div>
  )
}
