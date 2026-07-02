import { useNavigate } from 'react-router-dom'

/* 스플래시 — 앱 첫 진입. 다음: 면책 동의 */
export default function Splash() {
  const navigate = useNavigate()

  return (
    <div className="screen">
      <div className="splash">
        <div className="splash__logo">◷</div>
        <h1 className="title">운동하면 또 아픈 그 순간을 잡아주는 AI 트레이너</h1>
        <p className="subtitle">
          부상 부위로 부하가 쏠리는 패턴을 실시간으로 관찰하고,
          참고 정보형 피드백을 드려요.
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
