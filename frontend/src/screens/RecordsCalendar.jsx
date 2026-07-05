import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fmtDuration } from '../dummy.js'
import { fetchSessions } from '../api/sessions.js'
import { getDeviceId } from '../state/storage.js'

/* 기록 캘린더 — 운동한 날에 마커, 날짜 클릭 시 날짜별 상세로 이동.
   아래에는 최근 세션 리스트도 함께 보여준다.
   세션은 백엔드 GET /sessions 에서 현재 달 범위로 조회한다. */
const DOW = ['일', '월', '화', '수', '목', '금', '토']

function ymd(y, m, d) {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

export default function RecordsCalendar() {
  const navigate = useNavigate()
  // 기본은 이번 달 표시
  const now = new Date()
  const [cursor, setCursor] = useState({
    year: now.getFullYear(),
    month: now.getMonth(), // 0-based
  })
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const { year, month } = cursor
  const first = new Date(year, month, 1)
  const startDow = first.getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    const start = ymd(year, month, 1)
    const end = ymd(year, month, daysInMonth)
    fetchSessions(getDeviceId(), start, end)
      .then((data) => {
        if (cancelled) return
        setSessions(data.filter((s) => s.duration_s != null))
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
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cursor])

  const sessionDates = sessions.map((s) => s.date)

  const cells = []
  for (let i = 0; i < startDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  const move = (delta) => {
    const next = new Date(year, month + delta, 1)
    setCursor({ year: next.getFullYear(), month: next.getMonth() })
  }

  // 최근 세션 리스트: 시작 시각 내림차순
  const recent = [...sessions].sort((a, b) =>
    b.started_at.localeCompare(a.started_at),
  )

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">기록</p>
        <h2 className="title">운동 기록</h2>

        <div className="cal">
          <div className="cal__head">
            <button className="cal__nav" onClick={() => move(-1)}>
              ‹
            </button>
            <span className="cal__month">
              {year}년 {month + 1}월
            </span>
            <button className="cal__nav" onClick={() => move(1)}>
              ›
            </button>
          </div>

          <div className="cal__grid">
            {DOW.map((d) => (
              <div className="cal__dow" key={d}>
                {d}
              </div>
            ))}
            {cells.map((d, i) => {
              if (d === null) return <div key={`e${i}`} />
              const date = ymd(year, month, d)
              const has = sessionDates.includes(date)
              return (
                <button
                  key={date}
                  className={'cal__cell' + (has ? ' cal__cell--has' : '')}
                  disabled={!has}
                  onClick={() => navigate(`/app/records/${date}`)}
                >
                  {d}
                </button>
              )
            })}
          </div>
        </div>

        <p className="report-section-title">최근 세션</p>
        {loading ? (
          <p className="text-muted">불러오는 중...</p>
        ) : error ? (
          <p className="text-muted">{error}</p>
        ) : recent.length === 0 ? (
          <div className="detail-empty">
            아직 운동 기록이 없어요. 운동을 마치면 여기에 쌓여요.
          </div>
        ) : (
          recent.map((s) => (
            <button
              key={s.session_id}
              className="rec-row"
              onClick={() => navigate(`/app/records/${s.date}`)}
            >
              <span>
                <span className="rec-row__date">{s.date}</span>
                <span className="rec-row__sub">
                  스쿼트 · {fmtDuration(s.duration_s)} · {s.rep_count}회
                </span>
              </span>
              <span className="rec-row__chev">›</span>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
