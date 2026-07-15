import { useEffect, useRef, useState } from 'react'
import {
  FilesetResolver,
  PoseLandmarker,
  DrawingUtils,
} from '@mediapipe/tasks-vision'

const WASM_BASE_URL =
  'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm'
const MODEL_ASSET_PATH =
  'https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_lite/float16/latest/pose_landmarker_lite.task'

// backend/vision/feature_extractor.py의 CONFIDENCE_LANDMARK_IDXS와 반드시 동일해야 함
const CONFIDENCE_LANDMARK_IDXS = [11, 12, 23, 24, 25, 26, 27, 28, 31, 32]

async function openFrontPortraitCamera() {
  // iOS는 16:9 를 요청하면 센서를 가운데만 잘라(크롭) 줘서 화각이 좁아지고
  // 얼굴이 확대돼 보인다. 아이폰 기본 카메라와 같은 넓은 화각은 센서 전체를
  // 쓰는 4:3 이다 → 세로 기준 3:4(720x960)를 최우선으로 요청한다.
  // 주의: aspectRatio 제약은 iOS 에서 가로 프레임을 줘버리는 일이 있어 쓰지
  // 않는다. width < height 숫자 요청만으로 세로를 유도한다.
  const attempts = [
    {
      facingMode: 'user',
      width: { ideal: 720 },
      height: { ideal: 960 },
    },
    {
      facingMode: 'user',
      width: { ideal: 720 },
      height: { ideal: 1280 },
    },
    { facingMode: 'user' },
  ]

  let lastError = null
  for (const video of attempts) {
    try {
      return await navigator.mediaDevices.getUserMedia({ video })
    } catch (err) {
      if (
        err?.name === 'NotAllowedError' ||
        err?.name === 'SecurityError' ||
        err?.name === 'NotFoundError'
      ) {
        throw err
      }
      lastError = err
    }
  }
  throw lastError
}

async function applyMinimumCameraZoom(stream) {
  const [track] = stream.getVideoTracks()
  if (!track?.getCapabilities || !track?.applyConstraints) return

  const capabilities = track.getCapabilities()
  if (!('zoom' in capabilities)) return

  const zoom = capabilities.zoom?.min ?? 1
  try {
    await track.applyConstraints({ advanced: [{ zoom }] })
  } catch {
    // Some mobile browsers expose zoom but reject applying it.
  }
}

// 웹캠을 열고 MediaPipe PoseLandmarker로 매 프레임 랜드마크를 추출,
// canvas에 스켈레톤을 그려주는 공용 훅.
export function usePoseCamera() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  const [landmarks, setLandmarks] = useState(null)
  const [confidence, setConfidence] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)
  const [cameraStream, setCameraStream] = useState(null)

  useEffect(() => {
    let cancelled = false
    let poseLandmarker = null
    let stream = null
    let rafId = null
    let drawingUtils = null

    async function setup() {
      try {
        const vision = await FilesetResolver.forVisionTasks(WASM_BASE_URL)
        poseLandmarker = await PoseLandmarker.createFromOptions(vision, {
          baseOptions: {
            modelAssetPath: MODEL_ASSET_PATH,
            delegate: 'GPU',
          },
          runningMode: 'VIDEO',
          numPoses: 1,
        })

        // 전면 카메라. 폰 세로 화면에 맞게 '세로 영상'을 요청한다.
        // width < height 로 줘야 세로(720x1280) 프레임을 받아 화면이 세로로
        // 길게 나온다. (가로로 주면 세로 화면에 안 맞아 위아래 여백/가로로 보임)
        // 확대·줌 강제는 없음 — 기본 카메라 화각 그대로.
        stream = await openFrontPortraitCamera()
        await applyMinimumCameraZoom(stream)

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }
        setCameraStream(stream)

        const video = videoRef.current
        video.srcObject = stream
        await video.play()

        await new Promise((resolve) => {
          if (video.readyState >= 2) {
            resolve()
            return
          }
          video.addEventListener('loadeddata', resolve, { once: true })
        })

        if (cancelled) return

        if (canvasRef.current) {
          const ctx = canvasRef.current.getContext('2d')
          drawingUtils = new DrawingUtils(ctx)
        }

        setStatus('ready')

        const renderLoop = () => {
          if (cancelled) return

          const video = videoRef.current
          const result = poseLandmarker.detectForVideo(video, performance.now())
          const frameLandmarks = result.landmarks[0] ?? null

          setLandmarks(frameLandmarks)

          if (frameLandmarks) {
            const sum = CONFIDENCE_LANDMARK_IDXS.reduce(
              (acc, idx) => acc + (frameLandmarks[idx].visibility ?? 0),
              0,
            )
            setConfidence(sum / CONFIDENCE_LANDMARK_IDXS.length)
          } else {
            setConfidence(null)
          }

          const canvas = canvasRef.current
          if (canvas && drawingUtils && video.videoWidth && video.videoHeight) {
            if (
              canvas.width !== video.videoWidth ||
              canvas.height !== video.videoHeight
            ) {
              canvas.width = video.videoWidth
              canvas.height = video.videoHeight
            }
            const ctx = canvas.getContext('2d')
            ctx.save()
            ctx.clearRect(0, 0, canvas.width, canvas.height)
            if (frameLandmarks) {
              drawingUtils.drawLandmarks(frameLandmarks)
              drawingUtils.drawConnectors(
                frameLandmarks,
                PoseLandmarker.POSE_CONNECTIONS,
              )
            }
            ctx.restore()
          }

          rafId = requestAnimationFrame(renderLoop)
        }

        rafId = requestAnimationFrame(renderLoop)
      } catch (err) {
        if (cancelled) return
        setStatus('error')
        setError(err instanceof Error ? err.message : String(err))
      }
    }

    setup()

    return () => {
      cancelled = true
      if (rafId != null) cancelAnimationFrame(rafId)
      if (stream) stream.getTracks().forEach((track) => track.stop())
      if (poseLandmarker) poseLandmarker.close()
    }
  }, [])

  return {
    videoRef,
    canvasRef,
    landmarks,
    confidence,
    status,
    error,
    cameraStream,
  }
}
