import { useNavigate } from 'react-router-dom'
import { patternLabel } from '../dummy.js'
import { useProfileOrFallback } from '../state/ProfileContext.jsx'
import { useExercise } from '../state/ExerciseContext.jsx'

/* 운동 홈 — 오늘 할 운동 안내 + 시작.
   운동은 운동 선택 화면(A)에서 고른 것을 전역(useExercise)에서 읽는다.
   다음: 카메라 가드 */
export default function ExerciseHome() {
  const navigate = useNavigate()

  // 선택한 운동(없으면 기본=스쿼트로 폴백)
  const { exercise } = useExercise()

  // 온보딩에서 만든 관찰 프로필을 전역에서 읽는다 (없으면 폴백)
  const profile = useProfileOrFallback()
  const watchPatterns = profile.watch_patterns
  const focusAreas = profile.focus_areas

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">오늘의 운동</p>
        <h2 className="title">운동을 시작해볼까요?</h2>

        <div className="exercise-hero">
          <p className="exercise-hero__name">{exercise.name}</p>
          <p className="exercise-hero__sub">
            {exercise.parts.join(' · ')} 운동이에요. 다른 운동을 하고 싶으면
            아래에서 바꿀 수 있어요.
          </p>
          <button
            type="button"
            className="btn btn--ghost"
            style={{ marginTop: 12, width: 'auto', padding: '8px 16px' }}
            onClick={() => navigate('/app/exercise/select')}
          >
            운동 바꾸기
          </button>
        </div>

        {/* 온보딩에서 만든 집중 관찰 부위 */}
        <h3 className="field__label" style={{ marginTop: 8 }}>
          오늘 집중 관찰 부위
        </h3>
        <div className="tags">
          {focusAreas.map((fa) => (
            <span className="tag" key={fa.area}>
              {fa.area}
            </span>
          ))}
        </div>

        <h3 className="field__label" style={{ marginTop: 16 }}>
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
