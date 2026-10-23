/**
 * usePoseCamera.js
 * ----------------
 * Owns the video source (webcam OR a local video file) and the MediaPipe
 * PoseLandmarker running in LIVE_STREAM mode.
 *
 * LIVE_STREAM (not VIDEO) is what makes this realtime: it delivers results
 * via callback and drops frames when inference falls behind, instead of
 * queueing them and drifting further behind the source.
 *
 * The WASM runtime and the .task model are served from our own /mediapipe
 * path rather than a CDN, so the app works offline and inside sandboxed
 * previews with no external network.
 *
 * File mode exists because embedded preview iframes (and desktops with no
 * webcam) cannot open a camera. Feeding a recorded clip through the exact
 * same realtime pipeline keeps live mode demonstrable everywhere.
 */
import { useCallback, useEffect, useRef, useState } from 'react'

const WASM_PATH = '/mediapipe/wasm'
const MODEL_PATH = '/mediapipe/models/pose_landmarker_lite.task'

/**
 * Work out WHY a camera might be unavailable, so the UI can say something
 * more useful than "no camera found".
 */
export async function getCameraDiagnostics() {
  const inIframe = (() => {
    try { return window.self !== window.top } catch { return true }
  })()
  const secure = window.isSecureContext
  const hasApi = !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia)

  let videoInputs = -1
  let enumerateError = ''
  if (hasApi) {
    try {
      const devices = await navigator.mediaDevices.enumerateDevices()
      videoInputs = devices.filter((d) => d.kind === 'videoinput').length
    } catch (e) {
      enumerateError = e.message
    }
  }

  // Permissions-Policy tells us if an iframe was granted camera access.
  let policyAllowed = null
  try {
    const fp = document.featurePolicy || document.permissionsPolicy
    if (fp?.allowsFeature) policyAllowed = fp.allowsFeature('camera')
  } catch { /* not supported in this browser */ }

  return { inIframe, secure, hasApi, videoInputs, enumerateError, policyAllowed }
}

export function usePoseCamera({ onResult, enabled }) {
  const videoRef = useRef(null)
  const landmarkerRef = useRef(null)
  const streamRef = useRef(null)
  const rafRef = useRef(null)
  const objectUrlRef = useRef(null)
  const lastVideoTimeRef = useRef(-1)
  const onResultRef = useRef(onResult)
  const runningRef = useRef(false)
  const frameCountRef = useRef(0)

  const [status, setStatus] = useState('idle') // idle|loading|ready|running|error
  const [error, setError] = useState('')
  const [diagnostics, setDiagnostics] = useState(null)
  const [source, setSource] = useState(null) // 'camera' | 'file'
  const [fps, setFps] = useState(0)

  useEffect(() => { onResultRef.current = onResult }, [onResult])

  // ---- load the model once -------------------------------------------------
  useEffect(() => {
    if (!enabled) return
    let cancelled = false

    ;(async () => {
      try {
        setStatus('loading')
        const { FilesetResolver, PoseLandmarker } = await import('@mediapipe/tasks-vision')
        const fileset = await FilesetResolver.forVisionTasks(WASM_PATH)
        if (cancelled) return

        const options = {
          baseOptions: { modelAssetPath: MODEL_PATH },
          runningMode: 'LIVE_STREAM',
          numPoses: 1,
          minPoseDetectionConfidence: 0.5,
          minPosePresenceConfidence: 0.5,
          minTrackingConfidence: 0.5,
          outputSegmentationMasks: false,
        }
        let landmarker
        try {
          landmarker = await PoseLandmarker.createFromOptions(fileset, {
            ...options,
            baseOptions: { ...options.baseOptions, delegate: 'GPU' },
          })
        } catch {
          landmarker = await PoseLandmarker.createFromOptions(fileset, options)
        }
        if (cancelled) { landmarker.close?.(); return }

        landmarkerRef.current = landmarker
        setStatus('ready')
      } catch (e) {
        if (!cancelled) {
          setError(`Could not load the pose model: ${e.message}`)
          setStatus('error')
        }
      }
    })()

    return () => { cancelled = true }
  }, [enabled])

  // probe the environment up front so we can warn before they click
  useEffect(() => {
    if (!enabled) return
    getCameraDiagnostics().then(setDiagnostics)
  }, [enabled])

  // ---- fps meter -----------------------------------------------------------
  useEffect(() => {
    if (status !== 'running') { setFps(0); return }
    const id = setInterval(() => {
      setFps(frameCountRef.current)
      frameCountRef.current = 0
    }, 1000)
    return () => clearInterval(id)
  }, [status])

  // ---- frame pump ----------------------------------------------------------
  const pump = useCallback(() => {
    const video = videoRef.current
    const landmarker = landmarkerRef.current
    if (!runningRef.current || !video || !landmarker) return

    if (video.readyState >= 2 && video.currentTime !== lastVideoTimeRef.current) {
      lastVideoTimeRef.current = video.currentTime
      frameCountRef.current += 1
      try {
        landmarker.detectForVideo(video, performance.now(), (result) => {
          const lms = result?.landmarks?.[0] || null
          onResultRef.current?.(lms, performance.now() / 1000)
        })
      } catch (e) {
        runningRef.current = false
        streamRef.current?.getTracks().forEach((track) => track.stop())
        streamRef.current = null
        video.pause()
        video.srcObject = null
        setError(`Pose detection stopped: ${e.message}`)
        setStatus('error')
        return
      }
    }
    rafRef.current = requestAnimationFrame(pump)
  }, [])

  const beginPump = useCallback(() => {
    runningRef.current = true
    lastVideoTimeRef.current = -1
    frameCountRef.current = 0
    setStatus('running')
    rafRef.current = requestAnimationFrame(pump)
  }, [pump])

  // ---- camera --------------------------------------------------------------
  const start = useCallback(async () => {
    setError('')
    if (!landmarkerRef.current) {
      setError('Pose model is still loading, try again in a moment.')
      return false
    }

    const diag = await getCameraDiagnostics()
    setDiagnostics(diag)

    if (!diag.hasApi) {
      setError(
        diag.secure
          ? 'This browser does not expose a camera API.'
          : 'Camera needs a secure origin (HTTPS or localhost).'
      )
      setStatus('error')
      return false
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: 'user',
          width: { ideal: 640 },
          height: { ideal: 480 },
          frameRate: { ideal: 30 },
        },
        audio: false,
      })
      streamRef.current = stream
      const video = videoRef.current
      if (!video) return false
      video.srcObject = stream
      video.loop = false
      await video.play()

      setSource('camera')
      beginPump()
      return true
    } catch (e) {
      streamRef.current?.getTracks().forEach((track) => track.stop())
      streamRef.current = null
      // Blocked-by-iframe often surfaces as NotFoundError because the
      // device list is hidden from the frame entirely.
      const blockedByFrame = diag.inIframe && diag.policyAllowed === false
      let msg
      if (blockedByFrame) {
        msg = 'The preview frame is not allowed to use the camera. Open the preview in its own browser tab, or use a recorded video below.'
      } else if (e.name === 'NotAllowedError') {
        msg = 'Camera permission was denied. Allow camera access in your browser and try again.'
      } else if (e.name === 'NotFoundError' || e.name === 'OverconstrainedError') {
        msg = diag.videoInputs === 0
          ? (diag.inIframe
              ? 'No camera visible to this preview frame. Open the preview in its own tab, or use a recorded video below.'
              : 'No camera detected on this device. You can analyse a recorded video instead.')
          : 'The camera could not be opened with the requested settings.'
      } else if (e.name === 'NotReadableError') {
        msg = 'The camera is already in use by another app. Close it and retry.'
      } else {
        msg = `Could not start the camera: ${e.message}`
      }
      setError(msg)
      setStatus('error')
      return false
    }
  }, [beginPump])

  // ---- recorded file (fallback that uses the same live pipeline) ----------
  const startFile = useCallback(async (file, { onEnded } = {}) => {
    setError('')
    if (!landmarkerRef.current) {
      setError('Pose model is still loading, try again in a moment.')
      return false
    }
    const video = videoRef.current
    if (!video) return false

    try {
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
      const url = URL.createObjectURL(file)
      objectUrlRef.current = url

      video.srcObject = null
      video.src = url
      video.loop = false
      video.muted = true

      await new Promise((resolve, reject) => {
        const ok = () => { cleanup(); resolve() }
        const bad = () => { cleanup(); reject(new Error('Could not decode that video file')) }
        const cleanup = () => {
          video.removeEventListener('loadeddata', ok)
          video.removeEventListener('error', bad)
        }
        video.addEventListener('loadeddata', ok)
        video.addEventListener('error', bad)
      })

      const handleEnded = () => {
        video.removeEventListener('ended', handleEnded)
        onEnded?.()
      }
      video.addEventListener('ended', handleEnded)

      await video.play()
      setSource('file')
      beginPump()
      return true
    } catch (e) {
      setError(e.message || 'Could not play that video file.')
      setStatus('error')
      return false
    }
  }, [beginPump])

  // ---- stop ----------------------------------------------------------------
  const stop = useCallback(() => {
    runningRef.current = false
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    streamRef.current?.getTracks().forEach((t) => t.stop())
    streamRef.current = null
    const video = videoRef.current
    if (video) {
      video.pause?.()
      video.srcObject = null
      video.removeAttribute('src')
      video.load?.()
    }
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current)
      objectUrlRef.current = null
    }
    setSource(null)
    setStatus(landmarkerRef.current ? 'ready' : 'idle')
    setFps(0)
  }, [])

  // Always release the camera on unmount -- otherwise the recording
  // indicator stays lit after navigating away.
  useEffect(() => {
    return () => {
      runningRef.current = false
      if (rafRef.current) cancelAnimationFrame(rafRef.current)
      streamRef.current?.getTracks().forEach((t) => t.stop())
      if (objectUrlRef.current) URL.revokeObjectURL(objectUrlRef.current)
      landmarkerRef.current?.close?.()
      landmarkerRef.current = null
    }
  }, [])

  return { videoRef, status, error, fps, diagnostics, source, start, startFile, stop }
}
