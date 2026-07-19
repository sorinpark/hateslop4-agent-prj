import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { fmtDuration, fmtTime, fmtYYMMDD } from '../dummy.js'
import { fetchSessions } from '../api/sessions.js'
import { getDeviceId } from '../state/storage.js'
import { getExerciseBySlug } from '../exercises.js'

/* 기록 캘린더 — 운동한 날에 마커, 날짜 클릭 시 아래 '최근 세션' 리스트를 그
   날짜로 필터링(페이지 이동 없음). 다시 누르면 필터가 풀린다.
   세션은 백엔드 GET /sessions 에서 현재 달 범위로 조회한다. */
const DOW = ['일', '월', '화', '수', '목', '금', '토']

function ymd(y, m, d) {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

export default function RecordsCalendar() {
  const navigate = useNavigate()
  const location = useLocation()

  // 세션 리포트의 '되돌아가기'로 돌아온 경우, 그 세션의 날짜/달을 그대로 연다
  const returnDate = location.state?.selectedDate ?? null
  const returnYear = returnDate ? Number(returnDate.slice(0, 4)) : null
  const returnMonth = returnDate ? Number(returnDate.slice(5, 7)) - 1 : null

  // 기본은 이번 달 표시
  const now = new Date()
  const [cursor, setCursor] = useState({
    year: returnYear ?? now.getFullYear(),
    month: returnMonth ?? now.getMonth(), // 0-based
  })
  const [sessions, setSessions] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [selectedDate, setSelectedDate] = useState(returnDate)

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
    setSelectedDate(null)
  }

  // 최근 세션 리스트: 시작 시각 내림차순. 날짜를 선택했으면 그 날짜만.
  const recent = [...sessions]
    .filter((s) => !selectedDate || s.date === selectedDate)
    .sort((a, b) => b.started_at.localeCompare(a.started_at))

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
              const isSelected = date === selectedDate
              return (
                <button
                  key={date}
                  className={
                    'cal__cell' +
                    (has ? ' cal__cell--has' : '') +
                    (isSelected ? ' cal__cell--selected' : '')
                  }
                  disabled={!has}
                  onClick={() => setSelectedDate(isSelected ? null : date)}
                >
                  {d}
                </button>
              )
            })}
          </div>
        </div>

        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <p className="report-section-title" style={{ margin: 0 }}>
            이날의 운동
          </p>
          {selectedDate && (
            <button
              type="button"
              className="text-muted"
              style={{ background: 'none', border: 'none', cursor: 'pointer' }}
              onClick={() => setSelectedDate(null)}
            >
              전체 보기
            </button>
          )}
        </div>
        {loading ? (
          <p className="text-muted">불러오는 중...</p>
        ) : error ? (
          <p className="text-muted">{error}</p>
        ) : recent.length === 0 ? (
          <div className="detail-empty">
            {selectedDate ? (
              '이 날짜엔 운동 기록이 없어요.'
            ) : (
              <>
                아직 운동 기록이 없어요.
                <br />운동을 마치면 여기에 쌓여요.
              </>
            )}
          </div>
        ) : (
          recent.map((s) => (
            <button
              key={s.session_id}
              className="rec-row"
              onClick={() =>
                navigate('/app/records/report', {
                  state: { session: s, from: 'records' },
                })
              }
            >
              <span className="rec-row__date">
                {fmtYYMMDD(s.date)}-{fmtTime(s.started_at)} ·{' '}
                {getExerciseBySlug(s.exercise)?.name ?? s.exercise} ·{' '}
                {fmtDuration(s.duration_s)} · {s.rep_count}회
              </span>
              <span className="rec-row__chev">›</span>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
