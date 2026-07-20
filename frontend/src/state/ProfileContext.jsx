import { createContext, useContext, useState, useCallback } from 'react'
import { makeDummyProfile } from '../dummy.js'
import { loadJSON, saveJSON, STORAGE_KEYS, getDeviceId } from './storage.js'
import { createProfile } from '../api/profile.js'

/* 관찰 프로필 전역 상태 (localStorage 영속).
   온보딩(부상 입력 -> 프로필 생성)에서 확정한 schemas.ObservationProfile 을
   앱 전역에 흘려, 운동 홈 / 실시간 / 리포트가 같은 프로필을 참조하게 한다.
   프로필 탭에서 부상 이력을 수정하면 updateInjuries 로 반영된다.

   실제 연동 시: 프로필 생성/수정은 POST /profile 응답으로 setProfile 하면 된다.
   딥링크로 프로필 없이 진입하면 데모용 더미로 폴백한다. */
const ProfileContext = createContext(null)

// 프로필 없이 운동/기록에 바로 진입했을 때 쓰는 데모 폴백
const FALLBACK_PROFILE = makeDummyProfile([
  { part: '발목', side: 'right', condition: '족저근막염', discomfort: 3 },
])

export function ProfileProvider({ children }) {
  const [profile, setProfileState] = useState(() =>
    loadJSON(STORAGE_KEYS.profile, null),
  )

  // 프로필 통째 교체 + 저장
  const setProfile = useCallback((next) => {
    setProfileState(next)
    saveJSON(STORAGE_KEYS.profile, next)
  }, [])

  // 부상 이력(injuries)만 바꿔 프로필 재생성 (프로필 수정 화면용).
  // 백엔드 POST /profile 로 재생성 요청 — 실패 시 기존 프로필은 그대로 유지.
  const updateInjuries = useCallback(
    async (injuries) => {
      const next = await createProfile(injuries, getDeviceId())
      setProfileState(next)
      saveJSON(STORAGE_KEYS.profile, next)
      return next
    },
    [],
  )

  return (
    <ProfileContext.Provider value={{ profile, setProfile, updateInjuries }}>
      {children}
    </ProfileContext.Provider>
  )
}

// 원본 프로필(없으면 null). 온보딩 완료 여부 판단용.
export function useProfile() {
  const ctx = useContext(ProfileContext)
  if (!ctx) throw new Error('useProfile must be used within ProfileProvider')
  return ctx
}

// 항상 표시 가능한 프로필을 보장(없으면 폴백). 운동/리포트 화면용.
export function useProfileOrFallback() {
  const { profile } = useProfile()
  return profile ?? FALLBACK_PROFILE
}
