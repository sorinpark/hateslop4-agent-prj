import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { fmtDuration } from '../dummy.js'
import { useSessions } from '../state/SessionContext.jsx'

/* 기록 캘린더 — 운동한 날에 마커, 날짜 클릭 시 날짜별 상세로 이동.
   아래에는 최근 세션 리스트도 함께 보여준다.
   세션은 SessionContext(localStorage)에서 읽는다 — 실제 운동 기록이 반영됨. */
const DOW = ['일', '월', '화', '수', '목', '금', '토']

function ymd(y, m, d) {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

export default function RecordsCalendar() {
  const navigate = useNavigate()
  const { sessions, sessionDates } = useSessions()
  // 기본은 이번 달 표시
  const now = new Date()
  const [cursor, setCursor] = useState({
    year: now.getFullYear(),
    month: now.getMonth(), // 0-based
  })

  const { year, month } = cursor
  const first = new Date(year, month, 1)
  const startDow = first.getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const cells = []
  for (let i = 0; i < startDow; i++) cells.push(null)
  for (let d = 1; d <= daysInMonth; d++) cells.push(d)

  const move = (delta) => {
    const next = new Date(year, month + delta, 1)
    setCursor({ year: next.getFullYear(), month: next.getMonth() })
  }

  // 최근 세션 리스트: 최신순
  const recent = [...sessions].sort((a, b) =>
    b.session_id.localeCompare(a.session_id),
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
        {recent.length === 0 ? (
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
