/**
 * drawPose.js
 * -----------
 * Draws the skeleton overlay on a canvas sitting on top of the video.
 *
 * Landmarks are normalised (0-1), so they scale to whatever size the canvas
 * is rendered at. The canvas is mirrored to match the mirrored selfie view.
 */
import { POSE_CONNECTIONS } from './exerciseConfig'

const COLORS = {
  good: '#4ade80',
  warn: '#fbbf24',
  info: '#38bdf8',
  bone: 'rgba(255,255,255,0.55)',
  joint: '#ffffff',
}

export function drawPose(canvas, landmarks, opts = {}) {
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const { width: w, height: h } = canvas
  ctx.clearRect(0, 0, w, h)
  if (!landmarks) return

  const tone = opts.tone || 'info'
  const accent = COLORS[tone] || COLORS.info
  const highlight = new Set(opts.highlight || [])
  const visible = (p) => p && (p.visibility ?? 0) >= 0.5

  // bones
  ctx.lineWidth = Math.max(2, w / 180)
  ctx.lineCap = 'round'
  for (const [i, j] of POSE_CONNECTIONS) {
    const a = landmarks[i]
    const b = landmarks[j]
    if (!visible(a) || !visible(b)) continue
    const isTracked = highlight.has(i) && highlight.has(j)
    ctx.strokeStyle = isTracked ? accent : COLORS.bone
    ctx.lineWidth = isTracked ? Math.max(4, w / 110) : Math.max(2, w / 200)
    ctx.beginPath()
    ctx.moveTo(a.x * w, a.y * h)
    ctx.lineTo(b.x * w, b.y * h)
    ctx.stroke()
  }

  // joints
  for (let i = 0; i < landmarks.length; i++) {
    const p = landmarks[i]
    if (!visible(p)) continue
    // skip dense face points for a cleaner look
    if (i > 0 && i <= 10) continue
    const isTracked = highlight.has(i)
    ctx.fillStyle = isTracked ? accent : COLORS.joint
    ctx.beginPath()
    ctx.arc(p.x * w, p.y * h, isTracked ? Math.max(6, w / 90) : Math.max(3, w / 160), 0, Math.PI * 2)
    ctx.fill()
  }

  // angle readout at the tracked vertex
  if (opts.angle != null && opts.vertexIndex != null) {
    const v = landmarks[opts.vertexIndex]
    if (visible(v)) {
      const x = v.x * w
      const y = v.y * h
      const label = `${Math.round(opts.angle)}°`
      ctx.font = `700 ${Math.max(16, w / 26)}px Inter, system-ui, sans-serif`
      const tw = ctx.measureText(label).width
      const padX = 10
      const bh = Math.max(24, w / 20)

      // mirror-correct the text so it reads normally in the flipped view
      ctx.save()
      ctx.translate(x + 18, y - bh / 2 - 6)
      ctx.scale(-1, 1)
      ctx.fillStyle = 'rgba(11,16,32,0.82)'
      ctx.beginPath()
      ctx.roundRect(-(tw + padX * 2), 0, tw + padX * 2, bh, 8)
      ctx.fill()
      ctx.fillStyle = accent
      ctx.textBaseline = 'middle'
      ctx.fillText(label, -(tw + padX), bh / 2)
      ctx.restore()
    }
  }
}
