/* localStorage 영속 헬퍼.
   데모/오프라인 동안 세션·프로필을 유지한다.
   백엔드 연동 시 이 계층만 API 호출로 교체하면 된다. */

export function loadJSON(key, fallback) {
  try {
    const raw = localStorage.getItem(key)
    return raw ? JSON.parse(raw) : fallback
  } catch {
    return fallback
  }
}

export function saveJSON(key, value) {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    // 저장 실패(용량/사생활 모드 등)는 조용히 무시 — 메모리 상태는 유지됨
  }
}

export const STORAGE_KEYS = {
  profile: 'hateslop.profile',
  sessions: 'hateslop.sessions',
  deviceId: 'hateslop.device_id',
}

export function getDeviceId() {
  const existing = localStorage.getItem(STORAGE_KEYS.deviceId)
  if (existing) return existing

  const id = crypto.randomUUID()
  localStorage.setItem(STORAGE_KEYS.deviceId, id)
  return id
}
