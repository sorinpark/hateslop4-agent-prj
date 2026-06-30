import { useNavigate } from 'react-router-dom'
import { exercise, patternLabel } from '../dummy.js'

/* 운동 홈 — 오늘 할 운동(스쿼트) 안내 + 시작.
   다음: 카메라 가드 */
export default function ExerciseHome() {
  const navigate = useNavigate()

  // 더미: 관찰 프로필에서 넘어온다고 가정한 watch_patterns
  const watchPatterns = ['lr_imbalance', 'instability', 'load_shift']

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">오늘의 운동</p>
        <h2 className="title">운동을 시작해볼까요?</h2>

        <div className="exercise-hero">
          <p className="exercise-hero__name">{exercise.name}</p>
          <p className="exercise-hero__sub">
            큰 관절 위주라 인식이 안정적이에요. 1종으로 먼저 검증해요.
          </p>
        </div>

        <h3 className="field__label" style={{ marginTop: 8 }}>
          오늘 이 패턴들을 살펴봐요
        </h3>
        <div className="tags">
          {watchPatterns.map((p) => (
            <span className="tag" key={p}>
              {patternLabel[p] ?? p}
            </span>
          ))}
        </div>

        <div className="card card--soft" style={{ marginTop: 16 }}>
          <p className="text-muted" style={{ margin: 0 }}>
            운동 중 통증이 생기면 즉시 멈추고 전문가 상담을 권장해요. 이 앱의
            피드백은 패턴 관찰 기반 참고 정보예요.
          </p>
        </div>
      </div>

      <div className="screen__footer">
        <button
          className="btn btn--primary"
          onClick={() => navigate('/app/exercise/camera')}
        >
          카메라 준비하기
        </button>
      </div>
    </div>
  )
}
