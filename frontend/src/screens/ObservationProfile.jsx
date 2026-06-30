import { useNavigate, useLocation } from 'react-router-dom'
import {
  makeDummyProfile,
  patternLabel,
  categoryLabel,
  sideLabel,
} from '../dummy.js'

/* 관찰 프로필 — schemas.ObservationProfile 을 받아 표시한다.
   필드: user_id / injuries / focus_areas[{area,category,reason}]
         / watch_patterns / disclaimer
   지금은 API 대신 더미 프로필 사용 (입력된 injuries 만 끼워 넣음). */
export default function ObservationProfile() {
  const navigate = useNavigate()
  const location = useLocation()

  // 부상 입력 화면에서 넘어온 injuries (없으면 데모 기본값)
  const injuries = location.state?.injuries ?? [
    { part: '발목', side: 'right', condition: '족저근막염', discomfort: 3 },
  ]
  const profile = makeDummyProfile(injuries)

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
