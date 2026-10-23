/**
 * liveAnalyzer.js
 * ---------------
 * Realtime rep counting / hold timing, mirroring ExerciseAnalyzer in
 * app/ai/exercise_detector.py.
 *
 * Same state machine as the server: an angle above `up_angle` is the up
 * state, below `down_angle` is the down state, and a down->up transition
 * completes a rep. A rep that never passed the down threshold is a partial
 * and is counted against form -- once per rep, never per frame.
 *
 * Everything runs on the athlete's device. No video is uploaded; only the
 * final numbers are submitted.
 */
import { EXERCISE_CONFIG, LANDMARK, calculateAngle } from './exerciseConfig'

const VISIBILITY_THRESHOLD = 0.5

export class LiveAnalyzer {
  constructor(testType) {
    this.testType = testType
    this.cfg = EXERCISE_CONFIG[testType]
    if (!this.cfg) throw new Error(`Unknown test type: ${testType}`)
    this.kind = this.cfg.type
    this.reset()
  }

  reset() {
    this.stage = null
    this.reps = []
    this.holdSeconds = 0
    this.framesAnalysed = 0
    this.framesWithPose = 0
    this.currentPeak = null
    this.lastTs = null
    this.hipYSamples = []
    this.startedAt = null
    this.lastAngle = null
    this.cue = 'Get into position'
    this.cueTone = 'info'
    this.lastRepAt = null
    this.justCounted = false
  }

  /**
   * Feed one frame of landmarks.
   * @param {Array|null} landmarks 33 normalised landmarks, or null if no body
   * @param {number} tsSec monotonically increasing timestamp in seconds
   */
  addFrame(landmarks, tsSec) {
    if (this.startedAt === null) this.startedAt = tsSec
    this.framesAnalysed += 1
    this.justCounted = false

    const dt = this.lastTs === null ? 0 : Math.max(0, tsSec - this.lastTs)
    this.lastTs = tsSec

    if (!landmarks) {
      this.cue = 'Step into frame'
      this.cueTone = 'warn'
      this.lastAngle = null
      return
    }

    const [aName, bName, cName] = this.cfg.landmarks
    const a = landmarks[LANDMARK[aName]]
    const b = landmarks[LANDMARK[bName]]
    const c = landmarks[LANDMARK[cName]]

    const visible = [a, b, c].every(
      (p) => p && (p.visibility ?? 0) >= VISIBILITY_THRESHOLD
    )
    if (!visible) {
      this.cue = 'Move so your whole body is visible'
      this.cueTone = 'warn'
      this.lastAngle = null
      return
    }

    this.framesWithPose += 1
    const angle = calculateAngle(a, b, c)
    this.lastAngle = angle

    const hip = landmarks[LANDMARK.LEFT_HIP]
    if (hip && (hip.visibility ?? 0) >= VISIBILITY_THRESHOLD) {
      this.hipYSamples.push(hip.y)
    }

    if (this.kind === 'hold_based') this._trackHold(angle, dt)
    else this._trackReps(angle, tsSec)
  }

  _trackHold(angle, dt) {
    const lo = this.cfg.hold_angle_min ?? 0
    const hi = this.cfg.hold_angle_max ?? 360
    if (angle >= lo && angle <= hi) {
      this.holdSeconds += dt
      this.stage = 'holding'
      this.cue = this.cfg.cue_hold
      this.cueTone = 'good'
    } else {
      this.stage = 'broken'
      this.cue = this.cfg.cue_break
      this.cueTone = 'warn'
    }
  }

  _trackReps(angle, tsSec) {
    const up = this.cfg.up_angle
    const down = this.cfg.down_angle

    if (angle > up) {
      if (this.stage === 'down' && this.currentPeak !== null) {
        const bottomed = this.currentPeak <= down
        this.reps.push({ peak: this.currentPeak, bottomed, at: tsSec })
        this.currentPeak = null
        this.justCounted = true
        this.lastRepAt = tsSec
        this.cue = bottomed ? 'Good rep' : 'Too shallow - go deeper'
        this.cueTone = bottomed ? 'good' : 'warn'
      } else if (this.stage !== 'down') {
        this.cue = this.cfg.cue_down
        this.cueTone = 'info'
      }
      this.stage = 'up'
    } else if (angle < down) {
      if (this.stage === 'up') {
        this.stage = 'down'
        this.currentPeak = angle
      } else if (this.stage === 'down') {
        this.currentPeak = Math.min(this.currentPeak ?? angle, angle)
      }
      this.cue = this.cfg.cue_up
      this.cueTone = 'info'
    } else {
      if (this.stage === 'down' && this.currentPeak !== null) {
        this.currentPeak = Math.min(this.currentPeak, angle)
      }
      // Mid-range: nudge toward whichever end they're heading for.
      if (this.stage === 'up') {
        this.cue = this.cfg.cue_down
        this.cueTone = 'info'
      }
    }
  }

  get repCount() {
    return this.reps.length
  }

  get badFormReps() {
    return this.reps.filter((r) => !r.bottomed).length
  }

  get durationSec() {
    if (this.startedAt === null || this.lastTs === null) return 0
    return Math.max(0, this.lastTs - this.startedAt)
  }

  get coverage() {
    return this.framesAnalysed ? this.framesWithPose / this.framesAnalysed : 0
  }

  estimateJumpHeightCm() {
    if (this.hipYSamples.length < 10) return null
    const sorted = [...this.hipYSamples].sort((x, y) => x - y)
    const baseline = sorted[Math.floor(sorted.length * 0.75)]
    const peak = Math.min(...this.hipYSamples)
    return Math.round(Math.max(0, baseline - peak) * 200 * 10) / 10
  }

  /** Same four sub-scores the server computes, clamped 0-100. */
  calculateScore() {
    const reps = this.repCount
    const bad = this.badFormReps
    const total = Math.max(1, reps)
    const cleanRatio = reps ? (reps - bad) / total : 0
    const coverage = this.coverage
    const duration = this.durationSec

    let posture, balance, accuracy, speed
    if (this.kind === 'hold_based') {
      const volume = Math.min(100, (this.holdSeconds / 60) * 100)
      posture = 100 * coverage
      balance = volume
      accuracy = volume
      speed = volume
    } else {
      const volume = Math.min(100, reps * 5)
      posture = 100 * cleanRatio * (0.6 + 0.4 * coverage)
      balance = 100 * cleanRatio
      accuracy = volume * (0.5 + 0.5 * cleanRatio)
      const rate = duration > 0 ? reps / duration : 0
      speed = Math.min(100, (rate / 0.5) * 100)
    }

    const clamp = (v) => Math.max(0, Math.min(100, Math.round(v || 0)))
    const scores = {
      posture: clamp(posture),
      balance: clamp(balance),
      accuracy: clamp(accuracy),
      speed: clamp(speed),
    }
    scores.overall_score = clamp(
      (scores.posture + scores.balance + scores.accuracy + scores.speed) / 4
    )
    return scores
  }

  detectCheating() {
    const flags = []
    const duration = this.durationSec
    if (this.coverage < 0.5) flags.push('body_not_consistently_visible')
    if (duration < 2) flags.push('video_too_short')
    if (this.repCount > 0 && duration > 0 && this.repCount / duration > 3) {
      flags.push('implausible_rep_rate')
    }
    if (this.framesWithPose === 0) flags.push('no_person_detected')
    return flags
  }

  generateSuggestions(scores) {
    const name = this.cfg.display_name.toLowerCase()
    const out = []
    if (this.kind === 'hold_based') {
      if (this.holdSeconds < 20) out.push(`Try to extend your ${name} - aim for at least 30 seconds.`)
      if (scores.posture < 70) out.push('Keep your body in a straight line and your core braced.')
    } else {
      if (scores.accuracy < 60) out.push("Complete the full range of motion - partial reps don't count.")
      if (scores.posture < 70) out.push(`Watch your ${name} form - keep your back straight and controlled.`)
      if (scores.balance < 70) out.push('Your movement looks unstable; tighten your core for stability.')
      if (scores.speed < 50) out.push('Pick up the pace slightly while staying controlled.')
      if (this.badFormReps > 3) {
        out.push(`${this.badFormReps} reps didn't reach full depth - quality matters more than quantity.`)
      }
    }
    if (this.coverage < 0.7) out.push('Reposition the camera so your whole body stays in frame.')
    if (!out.length) out.push('Great performance! Keep this consistency up.')
    return out
  }

  /** Final payload, shaped exactly like AnalysisResult.to_dict() on the server. */
  finalize(source = 'live_camera') {
    const scores = this.calculateScore()
    const flags = this.detectCheating()
    const duration = this.durationSec
    const jump = this.kind === 'jump_based' ? this.estimateJumpHeightCm() : null

    let primary
    if (this.kind === 'hold_based') primary = Math.round(this.holdSeconds * 100) / 100
    else if (this.kind === 'jump_based') primary = jump ?? 0
    else primary = this.repCount

    return {
      test_type: this.testType,
      display_name: this.cfg.display_name,
      reps: this.repCount,
      hold_seconds: Math.round(this.holdSeconds * 100) / 100,
      jump_height_cm: jump,
      duration_sec: Math.round(duration * 100) / 100,
      bad_form_reps: this.badFormReps,
      frames_analysed: this.framesAnalysed,
      frames_with_pose: this.framesWithPose,
      pose_coverage: Math.round(this.coverage * 1000) / 1000,
      scores,
      suggestions: this.generateSuggestions(scores),
      cheat_detected: flags.length > 0,
      cheat_flags: flags,
      unit: this.cfg.unit,
      score: primary,
      source,
    }
  }
}
