const API_BASE_URL = import.meta.env.VITE_API_BASE_URL

export async function createProfile(injuries) {
  const res = await fetch(`${API_BASE_URL}/profile`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(injuries),
  })

  if (!res.ok) {
    const body = await res.json().catch(() => null)
    throw new Error(body?.detail ?? `프로필 생성 실패 (${res.status})`)
  }

  return res.json()
}
