import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { fmtDuration } from '../dummy.js'
import { fetchSessionReport } from '../api/sessions.js'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'

/* 세션 리포트 — 두 진입 경로가 이 화면을 공유한다:
   1) LiveExercise 에서 운동 종료 직후( from: 'live' ) — { session, report } 전달
   2) 기록 탭 캘린더에서 지난 세션 탭( from: 'records' ) — { session } 전달
   진입 경로에 따라 하단 버튼 구성이 다르다(아래 footer 참고).
   본문은 계약④ ReportSummary — 세션 중 쌓인 피드백을 AI가 1회 정리한
   총평 + 빈도별 항목 + 다음 세션 가이드(GET /sessions/{id}/report)로 보여준다. */
export default function SessionReport() {
  const navigate = useNavigate()
  const location = useLocation()

  const profile = useProfileOrFallback()

  const session = location.state?.session ?? null
  const from = location.state?.from ?? null

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
  const holdSeconds = session?.hold_seconds ?? 0
  const isHoldMode = holdSeconds > 0
  const feedbackCount = aiReport?.items.length ?? 0
  const nextGuidance = aiReport?.next_guidance ?? []
  const focusNames = profile.focus_areas.map((fa) => fa.area).join(', ')

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
            되돌아가기
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">세션 리포트</p>
        <h2 className="title">
          {from === 'records' ? '이 세션 정리했어요' : '오늘 운동 정리했어요'}
        </h2>
        <p className="subtitle">관찰 기준: {focusNames}</p>

        <div className="session-meta">
          <div className="session-meta__item">
            <div className="session-meta__value">{fmtDuration(durationSec)}</div>
            <div className="session-meta__label">운동 시간</div>
          </div>
          <div className="session-meta__item">
            <div className="session-meta__value">
              {isHoldMode ? `${Math.round(holdSeconds)}초` : repCount}
            </div>
            <div className="session-meta__label">
              {isHoldMode ? '유지 시간' : '횟수'}
            </div>
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

            {nextGuidance.length > 0 && (
              <>
                <p className="report-section-title">다음 세션 가이드</p>
                <div className="next-guidance">
                  {nextGuidance.map((item, i) => (
                    <div className="next-guidance__item" key={i}>
                      <span className="next-guidance__index">{i + 1}</span>
                      <span>{item}</span>
                    </div>
                  ))}
                </div>
              </>
            )}
          </>
        )}
      </div>

      <div className="screen__footer">
        {from === 'records' ? (
          <button
            className="btn btn--primary"
            onClick={() =>
              navigate('/app/records', {
                state: { selectedDate: session.date },
              })
            }
          >
            되돌아가기
          </button>
        ) : (
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
        )}
      </div>
    </div>
  )
}
