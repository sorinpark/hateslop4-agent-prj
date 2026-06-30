import { createContext, useContext, useState, useCallback } from 'react'
import { loadJSON, saveJSON, STORAGE_KEYS } from './storage.js'

/* 운동 세션 기록 전역 상태 (localStorage 영속).
   운동 종료 시 addSession 으로 쌓이고, 기록 묶음(캘린더/리스트/상세)이 읽는다.
   한 세션 형식:
     { session_id, date(YYYY-MM-DD), exercise, duration_s, rep_count,
       report: FeedbackMessage[] }
   백엔드 연동 시: addSession 은 POST /sessions, 목록은 GET /sessions 로 교체. */
const SessionContext = createContext(null)

// 로컬 날짜를 YYYY-MM-DD 로 (캘린더 매칭용, UTC 밀림 방지)
function todayLocal() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export function SessionProvider({ children }) {
  const [sessions, setSessions] = useState(() =>
    loadJSON(STORAGE_KEYS.sessions, []),
  )

  // 방금 끝난 운동을 기록에 추가하고 저장된 세션 객체를 반환
  const addSession = useCallback(({ exercise, durationSec, repCount, report }) => {
    const session = {
      session_id: `s_${Date.now()}`,
      date: todayLocal(),
      exercise,
      duration_s: durationSec,
      rep_count: repCount,
      report: report ?? [],
    }
    setSessions((prev) => {
      const next = [...prev, session]
      saveJSON(STORAGE_KEYS.sessions, next)
      return next
    })
    return session
  }, [])

  const value = {
    sessions,
    addSession,
    // 날짜로 세션 조회 (같은 날 여러 번이면 마지막 것)
    sessionByDate: (date) =>
      [...sessions].reverse().find((s) => s.date === date) ?? null,
    // 기록 있는 날짜 집합 (캘린더 마커)
    sessionDates: sessions.map((s) => s.date),
  }

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  )
}

export function useSessions() {
  const ctx = useContext(SessionContext)
  if (!ctx) throw new Error('useSessions must be used within SessionProvider')
  return ctx
}
