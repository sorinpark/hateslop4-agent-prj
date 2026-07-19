import { useEffect, useState } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { patternLabel, categoryLabel, sideLabel } from '../dummy.js'
import { useProfile } from '../state/ProfileContext.jsx'
import { createProfile } from '../api/profile.js'
import { getDeviceId } from '../state/storage.js'

/* 관찰 프로필 — schemas.ObservationProfile 을 받아 표시한다.
   필드: user_id / injuries / focus_areas[{area,category,reason}]
         / watch_patterns / disclaimer
   POST /profile 을 호출해 생성하고, 결과를 전역 Context 에 저장
   -> 운동/리포트가 같은 프로필 참조. */
export default function ObservationProfile() {
  const navigate = useNavigate()
  const location = useLocation()
  const { setProfile } = useProfile()

  const [profile, setLocalProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [retryKey, setRetryKey] = useState(0)

  // 부상 입력 화면에서 넘어온 injuries (없으면 데모 기본값)
  const stateInjuries = location.state?.injuries

  useEffect(() => {
    let ignore = false
    const injuries = stateInjuries ?? [
      { part: '발목', side: 'right', condition: '족저근막염', discomfort: 3 },
    ]

    setLoading(true)
    setError(null)

    createProfile(injuries, getDeviceId())
      .then((result) => {
        if (ignore) return
        setLocalProfile(result)
        setProfile(result)
        setLoading(false)
      })
      .catch((err) => {
        if (ignore) return
        setError(err.message)
        setLoading(false)
      })

    return () => {
      ignore = true
    }
  }, [stateInjuries, retryKey, setProfile])

  if (loading) {
    return (
      <div
        className="screen"
        style={{ alignItems: 'center', justifyContent: 'center' }}
      >
        <p className="text-muted">관찰 프로필을 만들고 있어요...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="screen">
        <p className="text-muted">{error}</p>
        <button
          className="btn btn--primary"
          onClick={() => setRetryKey((k) => k + 1)}
        >
          다시 시도
        </button>
      </div>
    )
  }

  if (!profile) return null

  return (
    <div className="screen">
      <div className="steps">
        <span className="steps__dot steps__dot--on" />
        <span className="steps__dot steps__dot--on" />
        <span className="steps__dot steps__dot--on" />
      </div>

      <div className="screen__scroll">
        <p className="eyebrow">3 / 3 · 관찰 프로필</p>
        <h2 className="title">이렇게 관찰할게요</h2>
        <p className="subtitle">
          입력하신 정보를 바탕으로, 운동 중 이 부위들을 중점적으로 살펴봐요.
        </p>

        {/* injuries 요약 */}
        <div className="card card--soft">
          {profile.injuries.map((inj, i) => (
            <p key={i} className="focus-reason" style={{ marginTop: i ? 6 : 0 }}>
              {sideLabel[inj.side]} {inj.part}
              {inj.condition ? ` · ${inj.condition}` : ''} · 불편감{' '}
              {inj.discomfort}/5
            </p>
          ))}
        </div>

        {/* focus_areas */}
        <h3 className="field__label" style={{ marginTop: 8 }}>
          집중 관찰 부위
        </h3>
        {profile.focus_areas.map((fa, i) => (
          <div className="card" key={i}>
            <div className="focus-row">
              <span className={`dot dot--${fa.category}`} />
              <div>
                <div className="focus-area">
                  {fa.area}{' '}
                  <span className="text-muted">
                    ({categoryLabel[fa.category]})
                  </span>
                </div>
                <div className="focus-reason">{fa.reason}</div>
              </div>
            </div>
          </div>
        ))}

        {/* watch_patterns */}
        <h3 className="field__label" style={{ marginTop: 8 }}>
          주의 깊게 볼 패턴
        </h3>
        <div className="tags">
          {profile.watch_patterns.map((p) => (
            <span className="tag" key={p}>
              {patternLabel[p] ?? p}
            </span>
          ))}
        </div>

        {/* disclaimer */}
        <span className="note-tag">{profile.disclaimer}</span>
      </div>

      <div className="screen__footer">
        <button
          className="btn btn--primary"
          onClick={() => navigate('/app/exercise')}
        >
          운동 시작하기
        </button>
        <button
          className="btn btn--ghost"
          style={{ marginTop: 10 }}
          onClick={() => navigate('/injury')}
        >
          입력 다시하기
        </button>
      </div>
    </div>
  )
}
