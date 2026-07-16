import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { exercise } from '../dummy.js'
import { createPoseLandmarker, computeConfidence } from '../lib/pose.js'

/* 카메라 가드 — 운동별 안내 + 실제 웹캠/MediaPipe 인식 신뢰도 체크 (기획.md 4-7-가).
   schemas.Confidence.below_threshold 가 true면 운동을 시작하지 않고 재안내한다. */
export default function CameraGuard() {
  const navigate = useNavigate()
  const videoRef = useRef(null)
  const rafRef = useRef(null)
  const landmarkerRef = useRef(null)
  const streamRef = useRef(null)
  const [confidence, setConfidence] = useState({
    overall: 0,
    interp_ratio: 0,
    below_threshold: true,
  })
  // 'loading' | 'ready' | 'denied' | 'error'
  const [status, setStatus] = useState('loading')

  useEffect(() => {
    let cancelled = false

    async function start() {
      let stream
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'user' },
        })
      } catch (err) {
        if (!cancelled) {
          setStatus(err.name === 'NotAllowedError' ? 'denied' : 'error')
        }
        return
      }
      if (cancelled) {
        stream.getTracks().forEach((t) => t.stop())
        return
      }
      streamRef.current = stream
      const video = videoRef.current
      video.srcObject = stream
      await video.play()

      try {
        const landmarker = await createPoseLandmarker()
        if (cancelled) {
          landmarker.close()
          return
        }
        landmarkerRef.current = landmarker
      } catch {
        if (!cancelled) setStatus('error')
        return
      }

      setStatus('ready')
      const loop = () => {
        if (cancelled || !videoRef.current || !landmarkerRef.current) return
        const result = landmarkerRef.current.detectForVideo(videoRef.current, performance.now())
        const landmarks = result.landmarks?.[0]
        if (landmarks) setConfidence(computeConfidence(landmarks))
        rafRef.current = requestAnimationFrame(loop)
      }
      loop()
    }

    start()

    return () => {
      cancelled = true
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      landmarkerRef.current?.close()
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
  }, [])

  const ok = status === 'ready' && !confidence.below_threshold

  return (
    <div className="screen">
      <div className="screen__scroll">
        <p className="eyebrow">카메라 준비 · {exercise.name}</p>
        <h2 className="title">카메라를 맞춰주세요</h2>
        <p className="subtitle">{exercise.cameraHint}</p>

        <div className="cam-preview">
          <video ref={videoRef} className="cam-preview__video" muted playsInline />
          {status === 'loading' && (
            <p className="text-muted" style={{ margin: 0, position: 'relative' }}>
              카메라를 불러오는 중...
            </p>
          )}
          {status === 'denied' && (
            <p className="text-muted" style={{ margin: 0, position: 'relative' }}>
              카메라 권한이 필요해요. 브라우저 설정에서 허용해주세요.
            </p>
          )}
          {status === 'error' && (
            <p className="text-muted" style={{ margin: 0, position: 'relative' }}>
              카메라를 불러오지 못했어요. 새로고침 후 다시 시도해주세요.
            </p>
          )}
        </div>

        {status === 'ready' && (
          <div className={'cam-status ' + (ok ? 'cam-status--ok' : 'cam-status--bad')}>
            <span
              className={
                'cam-status__dot ' + (ok ? 'cam-status__dot--ok' : 'cam-status__dot--bad')
              }
            />
            {ok
              ? `관절 인식 양호 (신뢰도 ${Math.round(confidence.overall * 100)}%)`
              : `관절이 잘 안 잡혀요 (신뢰도 ${Math.round(
                  confidence.overall * 100,
                )}%) — 카메라 위치를 다시 맞춰주세요`}
          </div>
        )}
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
