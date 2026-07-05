const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function fetchSessions(userId, startDate, endDate) {
  const res = await fetch(
    `${API_BASE_URL}/sessions?user_id=${encodeURIComponent(userId)}&start_date=${startDate}&end_date=${endDate}`,
  )

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `세션 목록 조회 실패 (${res.status})`)
  }

  return res.json()
}

export async function fetchSessionFeedback(sessionId) {
  const res = await fetch(`${API_BASE_URL}/sessions/${sessionId}/feedback`)

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `세션 피드백 조회 실패 (${res.status})`)
  }

  return res.json()
}
