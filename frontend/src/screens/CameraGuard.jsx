import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePoseCamera } from '../hooks/usePoseCamera.js'
import { useExercise } from '../state/ExerciseContext.jsx'

const CONFIDENCE_THRESHOLD = 0.6
// 양호 상태가 이만큼(ms) 이어지면 자동 캡처(한 프레임 튐으로 오작동 방지)
const CAPTURE_HOLD_MS = 800

/* 카메라 가드 — 운동별 안내 + 인식 신뢰도 체크 (기획.md 4-7-가).
   confidence < 0.6 이면 아직 인식이 덜 된 것으로 본다.

   전신이 안정적으로 잡히면(양호 상태가 잠깐 유지되면) 그 순간의 프레임을
   자동으로 캡처해 화면을 정지시킨다. 사용자가 '운동 시작' 버튼을 누르러
   카메라에 가까이 와 전신이 벗어나도, 정지된 캡처가 유지되므로 안심하고
   시작할 수 있다. 다시 맞추고 싶으면 '다시 맞추기'로 라이브로 돌아간다. */
export default function CameraGuard() {
  const navigate = useNavigate()
  const { exercise } = useExercise()
  const { videoRef, canvasRef, confidence, status, error, cameraStream } =
    usePoseCamera()

  // 현재 프레임 기준 인식 양호 여부(안내 문구용)
  const okNow = confidence !== null && confidence >= CONFIDENCE_THRESHOLD

  // 캡처된 정지 프레임을 그릴 캔버스 + 캡처 여부
  const captureCanvasRef = useRef(null)
  const bgVideoRef = useRef(null)
  const [captured, setCaptured] = useState(false)
  const holdTimerRef = useRef(null)

  useEffect(() => {
    const bgVideo = bgVideoRef.current
    if (!bgVideo || !cameraStream) return

    bgVideo.srcObject = cameraStream
    bgVideo.play().catch(() => {})
  }, [cameraStream])

  // 양호 상태가 CAPTURE_HOLD_MS 이상 이어지면 자동 캡처.
  // 이미 캡처됐으면 아무것도 안 함(다시 맞추기 전까지 정지 유지).
  useEffect(() => {
    if (captured) return
    if (okNow) {
      if (holdTimerRef.current == null) {
        holdTimerRef.current = setTimeout(() => {
          holdTimerRef.current = null
          doCapture()
        }, CAPTURE_HOLD_MS)
      }
    } else {
      // 양호가 끊기면 대기 타이머 취소(연속 유지됐을 때만 캡처)
      if (holdTimerRef.current != null) {
        clearTimeout(holdTimerRef.current)
        holdTimerRef.current = null
      }
    }
    return () => {
      if (holdTimerRef.current != null) {
        clearTimeout(holdTimerRef.current)
        holdTimerRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [okNow, captured])

  // 현재 video 프레임 + 스켈레톤을 캡처 캔버스에 그려 정지 이미지로 만든다.
  function doCapture() {
    const video = videoRef.current
    const skeleton = canvasRef.current
    const out = captureCanvasRef.current
    if (!video || !out || !video.videoWidth) return

    out.width = video.videoWidth
    out.height = video.videoHeight
    const ctx = out.getContext('2d')
    ctx.drawImage(video, 0, 0, out.width, out.height)
    // 스켈레톤 오버레이도 같이 얹어 '무엇이 잡혔는지' 보이게
    if (skeleton && skeleton.width && skeleton.height) {
      ctx.drawImage(skeleton, 0, 0, out.width, out.height)
    }
    setCaptured(true)
  }

  const retake = () => setCaptured(false)

  // 시작 가능 = 캡처됐거나(전신 잡혀 정지됨), 지금 양호함
  const canStart = captured || okNow

  return (
    <div className="screen ex-cam">
      <div className="screen__scroll">
        <p className="eyebrow eyebrow--tight">
          카메라 준비 · {exercise.name}
        </p>
        <p className="cam-hint">{exercise.cameraHint}</p>

        <div
          className="cam-preview cam-preview--live"
          style={{ position: 'relative' }}
        >
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

          {/* 라이브 영상 + 스켈레톤 (캡처되면 숨김).
              전면 카메라라 거울 모드(scaleX -1)로 보여준다 — 내가 왼쪽으로
              움직이면 화면에서도 왼쪽으로 움직이게. */}
          <video
            ref={bgVideoRef}
            className="camera-video-bg"
            muted
            playsInline
            autoPlay
            aria-hidden="true"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: captured ? 'none' : 'block',
            }}
          />
          <video
            ref={videoRef}
            className="camera-video-main"
            muted
            playsInline
            autoPlay
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: captured ? 'none' : 'block',
              transform: 'scaleX(-1)',
            }}
          />
          <canvas
            ref={canvasRef}
            className="camera-overlay-main"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: captured ? 'none' : 'block',
              transform: 'scaleX(-1)',
            }}
          />
          {/* 캡처된 정지 프레임 (캡처됐을 때만 보임). 라이브와 같은 거울 방향 유지 */}
          <canvas
            ref={captureCanvasRef}
            className="camera-overlay-main"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: '100%',
              height: '100%',
              display: captured ? 'block' : 'none',
              transform: 'scaleX(-1)',
            }}
          />
          {captured && <span className="cam-captured-badge">촬영됨</span>}

          {/* 상태표시를 카메라 위 오버레이(하단)로 얹어 세로 공간을 아낀다 */}
          <div
            className={
              'cam-status cam-status--overlay ' +
              (captured || okNow ? 'cam-status--ok' : 'cam-status--bad')
            }
          >
            <span
              className={
                'cam-status__dot ' +
                (captured || okNow ? 'cam-status__dot--ok' : 'cam-status__dot--bad')
              }
            />
            {captured
              ? '전신이 잘 잡혔어요 — 그대로 시작하세요.'
              : confidence === null
                ? '아직 인식되지 않았어요'
                : okNow
                  ? `관절 인식 양호 (${Math.round(confidence * 100)}%)`
                  : `관절이 잘 안 잡혀요 (${Math.round(
                      confidence * 100,
                    )}%) — 위치를 다시 맞춰주세요`}
          </div>
        </div>
      </div>

      <div className="screen__footer">
        {/* 캡처됐을 때만 '다시 맞추기'가 생기며, 두 버튼을 가로로 나란히 둔다 */}
        <div className={captured ? 'btn-row' : ''}>
          {captured && (
            <button className="btn btn--ghost" onClick={retake}>
              다시 맞추기
            </button>
          )}
          <button
            className="btn btn--primary"
            disabled={!canStart}
            onClick={() => navigate('/app/exercise/live')}
          >
            {canStart ? '운동 시작' : '전신이 잡히면 시작할 수 있어요'}
          </button>
        </div>
      </div>
    </div>
  )
}
