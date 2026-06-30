import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { exercise, dummyConfidence } from '../dummy.js'

/* 카메라 가드 — 운동별 안내 + 인식 신뢰도 체크 (기획.md 4-7-가).
   schemas.Confidence.below_threshold 가 true면 운동을 시작하지 않고 재안내한다.
   여기선 카메라 연동 전이라 신뢰도를 토글로 시연한다. */
export default function CameraGuard() {
  const navigate = useNavigate()
  // 더미: 실제로는 vision 이 매 프레임 confidence 를 올려준다
  const [confidence, setConfidence] = useState(dummyConfidence)

  const ok = !confidence.below_threshold && confidence.overall >= 0.6

  const toggleDummy = () =>
    setConfidence((c) =>
      c.below_threshold
        ? { ...c, overall: 0.92, below_threshold: false }
        : { ...c, overall: 0.34, below_threshold: true },
    )

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">카메라 준비 · {exercise.name}</p>
        <h2 className="title">카메라를 맞춰주세요</h2>
        <p className="subtitle">{exercise.cameraHint}</p>

        <div className="cam-preview">
          <span className="cam-preview__icon">📷</span>
          <p className="text-muted" style={{ margin: 0 }}>
            (카메라 프리뷰 자리 — vision 연동 시 실제 영상 표시)
          </p>
        </div>

        <div className={'cam-status ' + (ok ? 'cam-status--ok' : 'cam-status--bad')}>
          <span
            className={
              'cam-status__dot ' +
              (ok ? 'cam-status__dot--ok' : 'cam-status__dot--bad')
            }
          />
          {ok
            ? `관절 인식 양호 (신뢰도 ${Math.round(confidence.overall * 100)}%)`
            : `관절이 잘 안 잡혀요 (신뢰도 ${Math.round(
                confidence.overall * 100,
              )}%) — 카메라 위치를 다시 맞춰주세요`}
        </div>

        {/* 시연용 토글 — 실제 빌드에선 제거 (vision 신뢰도가 대체) */}
        <button className="btn btn--ghost" onClick={toggleDummy}>
          (시연용) 인식 상태 바꿔보기
        </button>
      </div>

      <div className="screen__footer">
        <button
          className="btn btn--primary"
          disabled={!ok}
          onClick={() => navigate('/app/exercise/live')}
        >
          {ok ? '운동 시작' : '인식되면 시작할 수 있어요'}
        </button>
      </div>
    </div>
  )
}
