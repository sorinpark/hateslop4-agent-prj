import { useNavigate } from 'react-router-dom'
import { exercise } from '../dummy.js'
import { usePoseCamera } from '../hooks/usePoseCamera.js'

/* 카메라 가드 — 운동별 안내 + 인식 신뢰도 체크 (기획.md 4-7-가).
   confidence < 0.6 이면 운동을 시작하지 않고 재안내한다. */
export default function CameraGuard() {
  const navigate = useNavigate()
  const { videoRef, canvasRef, confidence, status, error } = usePoseCamera()

  const ok = confidence !== null && confidence >= 0.6

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">카메라 준비 · {exercise.name}</p>
        <h2 className="title">카메라를 맞춰주세요</h2>
        <p className="subtitle">{exercise.cameraHint}</p>

        <div className="cam-preview" style={{ position: 'relative' }}>
          {status === 'loading' && (
            <p className="text-muted" style={{ margin: 0 }}>
              카메라를 준비하고 있어요...
            </p>
          )}

          {status === 'error' && (
            <p className="text-muted" style={{ margin: 0 }}>
              카메라 접근에 실패했어요. 브라우저 카메라 권한을 확인해주세요.
              {error ? ` (${error})` : ''}
            </p>
          )}

          <video
            ref={videoRef}
            muted
            playsInline
            autoPlay
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              transform: 'scaleX(-1)',
            }}
          />
          <canvas
            ref={canvasRef}
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              transform: 'scaleX(-1)',
            }}
          />
        </div>

        <div className={'cam-status ' + (ok ? 'cam-status--ok' : 'cam-status--bad')}>
          <span
            className={
              'cam-status__dot ' +
              (ok ? 'cam-status__dot--ok' : 'cam-status__dot--bad')
            }
          />
          {confidence === null
            ? '아직 인식되지 않았어요'
            : ok
              ? `관절 인식 양호 (신뢰도 ${Math.round(confidence * 100)}%)`
              : `관절이 잘 안 잡혀요 (신뢰도 ${Math.round(
                  confidence * 100,
                )}%) — 카메라 위치를 다시 맞춰주세요`}
        </div>
      </div>

      <div className="screen__footer">
        {!ok && (
          <p className="text-muted">
            인식이 안정적이지 않아요. 조명을 밝게 하거나 배경과 대비되는 옷을
            입으면 도움이 될 수 있어요.
          </p>
        )}
        <button
          className="btn btn--primary"
          onClick={() => navigate('/app/exercise/live')}
        >
          운동 시작
        </button>
      </div>
    </div>
  )
}
