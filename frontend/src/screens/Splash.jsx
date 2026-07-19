import { useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useProfile } from '../state/ProfileContext.jsx'

/* 스플래시 — 앱 첫 진입. 다음: 면책 동의 */
export default function Splash() {
  const navigate = useNavigate()
  const { profile } = useProfile()

  useEffect(() => {
    if (profile) {
      navigate('/app/exercise', { replace: true })
    }
  }, [profile, navigate])

  return (
    <div className="screen">
      <div className="splash">
        <div className="splash__logo">
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="currentColor"
            aria-hidden="true"
            style={{ transform: 'scaleX(-1)' }}
          >
            <path d="M20.57 14.86L22 13.43 20.57 12 17 15.57 8.43 7 12 3.43 10.57 2 9.14 3.43 7.71 2 5.57 4.14 4.14 2.71 2.71 4.14l1.43 1.43L2 7.71l1.43 1.43L2 10.57 3.43 12 7 8.43 15.57 17 12 20.57 13.43 22l1.43-1.43L16.29 22l2.14-2.14 1.43 1.43 1.43-1.43-1.43-1.43L22 16.29z" />
          </svg>
        </div>
        <h1 className="title">부상 맞춤 AI 트레이너</h1>
        <p className="subtitle">
          운동 중 아픈 부위에 무리가 가지 않는지
          <br />실시간으로 지켜봐요.
        </p>
      </div>
      <div className="screen__footer">
        <button className="btn btn--primary" onClick={() => navigate('/disclaimer')}>
          시작하기
        </button>
      </div>
    </div>
  )
}
