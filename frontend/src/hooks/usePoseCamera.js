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

// 웹캠을 열고 MediaPipe PoseLandmarker로 매 프레임 랜드마크를 추출,
// canvas에 스켈레톤을 그려주는 공용 훅.
export function usePoseCamera() {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)

  const [landmarks, setLandmarks] = useState(null)
  const [confidence, setConfidence] = useState(null)
  const [status, setStatus] = useState('loading')
  const [error, setError] = useState(null)

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

        stream = await navigator.mediaDevices.getUserMedia({ video: true })

        if (cancelled) {
          stream.getTracks().forEach((track) => track.stop())
          return
        }

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

  return { videoRef, canvasRef, landmarks, confidence, status, error }
}
