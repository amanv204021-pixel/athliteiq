/**
 * Live.jsx
 * --------
 * Realtime assessment: the phone/laptop camera feeds MediaPipe running
 * on-device, reps are counted as you move, and only the final numbers are
 * submitted to the server. No video ever leaves the device.
 */
import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { calculateAngle, EXERCISE_CONFIG, LANDMARK, LIVE_TESTS } from '../live/exerciseConfig'
import { LiveAnalyzer } from '../live/liveAnalyzer'
import { drawPose } from '../live/drawPose'
import { usePoseCamera } from '../live/usePoseCamera'

const COUNTDOWN_FROM = 3

export default function Live() {
  const nav = useNavigate()
  const canvasRef = useRef(null)
  const analyzerRef = useRef(null)
  const beepRef = useRef(null)
  const fileRef = useRef(null)

  const [testType, setTestType] = useState('squat')
  const [phase, setPhase] = useState('setup') // setup|countdown|active|done
  const [countdown, setCountdown] = useState(COUNTDOWN_FROM)
  const [live, setLive] = useState({ reps: 0, hold: 0, angle: null, cue: '', tone: 'info', stage: null })
  const [result, setResult] = useState(null)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const [elapsed, setElapsed] = useState(0)

  const cfg = EXERCISE_CONFIG[testType]
  const isHold = cfg.type === 'hold_based'

  // --- short beep on each rep, built with WebAudio (no asset needed) --------
  const beep = useCallback((ok = true) => {
    try {
      if (!beepRef.current) {
        beepRef.current = new (window.AudioContext || window.webkitAudioContext)()
      }
      const ac = beepRef.current
      const osc = ac.createOscillator()
      const gain = ac.createGain()
      osc.frequency.value = ok ? 880 : 320
      gain.gain.setValueAtTime(0.12, ac.currentTime)
      gain.gain.exponentialRampToValueAtTime(0.001, ac.currentTime + 0.14)
      osc.connect(gain).connect(ac.destination)
      osc.start()
      osc.stop(ac.currentTime + 0.15)
    } catch { /* audio is a nicety, never block on it */ }
  }, [])

  // --- per-frame callback ---------------------------------------------------
  const handleResult = useCallback((landmarks, tsSec) => {
    const canvas = canvasRef.current
    const analyzer = analyzerRef.current

    // indices we highlight = the three joints this exercise tracks
    const tracked = cfg.landmarks.map((n) => LANDMARK[n])
    let angle = null
    let tone = 'info'

    if (analyzer && phaseRef.current === 'active') {
      analyzer.addFrame(landmarks, tsSec)
      angle = analyzer.lastAngle
      tone = analyzer.cueTone
      if (analyzer.justCounted) {
        const lastRep = analyzer.reps[analyzer.reps.length - 1]
        beep(lastRep?.bottomed)
      }
      setLive({
        reps: analyzer.repCount,
        hold: analyzer.holdSeconds,
        angle: analyzer.lastAngle,
        cue: analyzer.cue,
        tone: analyzer.cueTone,
        stage: analyzer.stage,
      })
      setElapsed(analyzer.durationSec)
    } else if (landmarks) {
      // pre-start: still show the skeleton so they can frame themselves
      const [a, b, c] = cfg.landmarks.map((n) => landmarks[LANDMARK[n]])
      if (a && b && c) angle = calculateAngle(a, b, c)
    }

    drawPose(canvas, landmarks, {
      tone,
      highlight: tracked,
      angle,
      vertexIndex: LANDMARK[cfg.landmarks[1]],
    })
  }, [cfg, beep])

  // keep a ref of phase so the rAF callback sees the current value
  const phaseRef = useRef(phase)
  useEffect(() => { phaseRef.current = phase }, [phase])

  const { videoRef, status, error, fps, diagnostics, source, start, startFile, stop } =
    usePoseCamera({ onResult: handleResult, enabled: true })

  // size the canvas to the video once it has dimensions
  useEffect(() => {
    const v = videoRef.current
    const c = canvasRef.current
    if (!v || !c) return
    const onMeta = () => {
      c.width = v.videoWidth || 640
      c.height = v.videoHeight || 480
    }
    v.addEventListener('loadedmetadata', onMeta)
    return () => v.removeEventListener('loadedmetadata', onMeta)
  }, [videoRef])

  // --- countdown ------------------------------------------------------------
  useEffect(() => {
    if (phase !== 'countdown') return
    if (countdown <= 0) {
      analyzerRef.current = new LiveAnalyzer(testType)
      setPhase('active')
      return
    }
    const t = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(t)
  }, [phase, countdown, testType])

  const begin = async () => {
    setResult(null)
    setSaveMsg('')
    if (status !== 'running') {
      const ok = await start()
      if (!ok) return
    }
    setCountdown(COUNTDOWN_FROM)
    setPhase('countdown')
  }

  const beginWithFile = async (file) => {
    if (!file) return
    setResult(null)
    setSaveMsg('')
    // Analysis starts as soon as the clip plays; when it ends we score it.
    const ok = await startFile(file, { onEnded: () => finishRef.current?.() })
    if (!ok) return
    analyzerRef.current = new LiveAnalyzer(testType)
    setPhase('active')
  }

  const finish = () => {
    const analyzer = analyzerRef.current
    if (!analyzer) return
    const payload = analyzer.finalize(source === 'file' ? 'local_video' : 'live_camera')
    setResult(payload)
    setPhase('done')
    stop()
  }

  const finishRef = useRef(null)
  useEffect(() => { finishRef.current = finish })

  const reset = () => {
    analyzerRef.current = null
    setResult(null)
    setSaveMsg('')
    setLive({ reps: 0, hold: 0, angle: null, cue: '', tone: 'info', stage: null })
    setElapsed(0)
    setPhase('setup')
  }

  const save = async () => {
    if (!result) return
    setSaving(true)
    setSaveMsg('')
    try {
      await api.submitLive(testType, result)
      setSaveMsg('Saved. Your result is on your dashboard and the leaderboard.')
    } catch (e) {
      setSaveMsg(`Could not save: ${e.message}`)
    } finally {
      setSaving(false)
    }
  }

  const busy = status === 'loading'

  return (
    <div className="container page">
      <div className="spread mb">
        <div>
          <h1 className="h1">Live assessment</h1>
          <p className="sub" style={{ marginBottom: 0 }}>
            Real-time pose tracking on your device. Your video never leaves your phone.
          </p>
        </div>
        {status === 'running' && (
          <span className="badge badge-ok">
            {source === 'file' ? 'analysing clip' : 'live'}{fps > 0 ? ` · ${fps} fps` : ''}
          </span>
        )}
      </div>

      {error && (
        <div className="alert alert-error">
          <div>{error}</div>
          {diagnostics && (
            <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
              Diagnostics — cameras visible: <b>{diagnostics.videoInputs < 0 ? 'unknown' : diagnostics.videoInputs}</b>
              {' · '}in iframe: <b>{String(diagnostics.inIframe)}</b>
              {' · '}secure context: <b>{String(diagnostics.secure)}</b>
              {diagnostics.policyAllowed !== null && <> · frame allows camera: <b>{String(diagnostics.policyAllowed)}</b></>}
            </div>
          )}
        </div>
      )}

      {phase === 'setup' && status !== 'running' && !error && diagnostics && (
        <>
          {!diagnostics.secure && (
            <div className="alert alert-error">
              <b>Camera blocked: insecure connection.</b> Browsers only allow
              camera access over <code>https://</code> or <code>localhost</code>.
              You're on <code>{window.location.protocol}//{window.location.hostname}</code>.
              Run <code>./scripts/run_local.sh --https</code> to fix this.
            </div>
          )}
          {diagnostics.secure && diagnostics.policyAllowed === false && (
            <div className="alert alert-info">
              <b>This preview frame blocks camera access.</b> The camera itself
              is fine — the embedding page just isn't permitted to use it.
              Open the app directly at <code>http://localhost:8000/live</code>,
              or analyse a recorded clip below.
            </div>
          )}
          {diagnostics.secure && diagnostics.videoInputs === 0 &&
           diagnostics.policyAllowed !== false && (
            <div className="alert alert-info">
              No camera is visible to this page. If this machine has a webcam,
              it's likely blocked by the embedding frame — open
              <code> http://localhost:8000/live</code> directly, or analyse a
              recorded clip below.
            </div>
          )}
        </>
      )}
      {busy && <div className="alert alert-info"><span className="spinner" /> Loading the pose model (one-time, ~6 MB)…</div>}

      <div className="grid grid-2">
        {/* ---------------- camera ---------------- */}
        <div className="card" style={{ padding: 12 }}>
          <div className="live-stage">
            <video ref={videoRef} playsInline muted className="live-video" />
            <canvas ref={canvasRef} className="live-canvas" />

            {phase === 'countdown' && (
              <div className="live-overlay">
                <div className="countdown">{countdown === 0 ? 'GO' : countdown}</div>
              </div>
            )}

            {status !== 'running' && phase === 'setup' && (
              <div className="live-overlay live-overlay-dim">
                <div style={{ textAlign: 'center', padding: 20 }}>
                  <div style={{ fontSize: 15, fontWeight: 600, marginBottom: 6 }}>
                    Camera is off
                  </div>
                  <div className="muted" style={{ fontSize: 13 }}>
                    Stand side-on, full body in frame, about 2 m back.
                  </div>
                </div>
              </div>
            )}

            {phase === 'active' && (
              <div className={`live-cue live-cue-${live.tone}`}>{live.cue}</div>
            )}
          </div>

          <div className="row mt" style={{ justifyContent: 'center' }}>
            {phase === 'setup' && (
              <button className="btn" onClick={begin} disabled={busy}>
                {status === 'running' ? 'Start test' : 'Enable camera & start'}
              </button>
            )}
            {(phase === 'countdown' || phase === 'active') && (
              <>
                <button className="btn" onClick={finish} disabled={phase === 'countdown'}>
                  Finish & score
                </button>
                <button className="btn btn-ghost" onClick={() => { stop(); reset() }}>
                  Cancel
                </button>
              </>
            )}
            {phase === 'done' && (
              <button className="btn btn-ghost" onClick={reset}>Try again</button>
            )}
          </div>

          {phase === 'setup' && (
            <div className="mt" style={{ textAlign: 'center' }}>
              <div className="muted" style={{ fontSize: 12, marginBottom: 8 }}>
                No camera here? Run a recorded clip through the same live engine.
              </div>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => fileRef.current?.click()}
                disabled={busy}
              >
                Analyse a recorded video
              </button>
              <input
                ref={fileRef}
                type="file"
                accept="video/*"
                style={{ display: 'none' }}
                onChange={(e) => {
                  const f = e.target.files?.[0]
                  e.target.value = ''
                  beginWithFile(f)
                }}
              />
            </div>
          )}
        </div>

        {/* ---------------- live stats ---------------- */}
        <div>
          <div className="card mb">
            <label style={{ marginTop: 0 }}>Exercise</label>
            <select
              value={testType}
              onChange={(e) => setTestType(e.target.value)}
              disabled={phase === 'active' || phase === 'countdown'}
            >
              {LIVE_TESTS.map((k) => (
                <option key={k} value={k}>{EXERCISE_CONFIG[k].display_name}</option>
              ))}
            </select>

            <div className="live-counter mt">
              <div className="live-counter-value">
                {isHold ? live.hold.toFixed(1) : live.reps}
              </div>
              <div className="live-counter-label">
                {isHold ? 'seconds held' : 'reps'}
              </div>
            </div>

            <div className="grid grid-3 mt">
              <div>
                <div className="muted">Angle</div>
                <b>{live.angle != null ? `${Math.round(live.angle)}°` : '—'}</b>
              </div>
              <div>
                <div className="muted">Stage</div>
                <b style={{ textTransform: 'capitalize' }}>{live.stage || '—'}</b>
              </div>
              <div>
                <div className="muted">Time</div>
                <b>{elapsed.toFixed(1)}s</b>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="card-title">How to get a clean read</div>
            <ul className="muted" style={{ paddingLeft: 18, lineHeight: 1.9, fontSize: 13 }}>
              <li>Stand <b>side-on</b> to the camera — angles are measured from your left side.</li>
              <li>Keep your <b>whole body</b> in frame, roughly 2 m away.</li>
              <li>Good, even lighting; avoid strong backlight.</li>
              <li>Partial reps are detected and won't count.</li>
            </ul>
          </div>
        </div>
      </div>

      {result && <LiveResult result={result} onSave={save} saving={saving} saveMsg={saveMsg} onDone={() => nav('/dashboard')} />}
    </div>
  )
}

function LiveResult({ result, onSave, saving, saveMsg, onDone }) {
  const s = result.scores || {}
  return (
    <div className="card mt">
      <div className="spread mb">
        <div className="card-title" style={{ margin: 0 }}>{result.display_name} — result</div>
        <span className={`badge ${result.cheat_detected ? 'badge-warn' : 'badge-ok'}`}>
          {result.source === 'local_video' ? 'local video' : 'live camera'}
          {result.cheat_detected ? ' · needs review' : ''}
        </span>
      </div>

      <div style={{ fontSize: 44, fontWeight: 900, letterSpacing: -2 }}>
        {result.score}
        <span style={{ fontSize: 16, color: 'var(--muted)' }}> {result.unit}</span>
      </div>

      {result.cheat_detected && (
        <div className="alert alert-info">
          Flagged: {result.cheat_flags.join(', ').replace(/_/g, ' ')}. A scout will
          verify before this reaches the leaderboard.
        </div>
      )}

      <div className="grid grid-4 mt">
        {['posture', 'balance', 'accuracy', 'speed'].map((k) => (
          <div key={k}>
            <div className="spread">
              <span className="muted" style={{ textTransform: 'capitalize' }}>{k}</span>
              <b>{s[k] ?? 0}</b>
            </div>
            <div className="bar"><i style={{ width: `${s[k] ?? 0}%` }} /></div>
          </div>
        ))}
      </div>

      <div className="grid grid-4 mt">
        <div><div className="muted">Reps</div><b>{result.reps}</b></div>
        <div><div className="muted">Partial reps</div><b>{result.bad_form_reps}</b></div>
        <div><div className="muted">Duration</div><b>{result.duration_sec}s</b></div>
        <div><div className="muted">Coverage</div><b>{Math.round(result.pose_coverage * 100)}%</b></div>
      </div>

      <div className="card-title mt">Coach feedback</div>
      <ul style={{ paddingLeft: 18 }}>
        {result.suggestions.map((t, i) => (
          <li key={i} className="muted" style={{ marginBottom: 6 }}>{t}</li>
        ))}
      </ul>

      {saveMsg && (
        <div className={`alert ${saveMsg.startsWith('Saved') ? 'alert-ok' : 'alert-error'}`}>
          {saveMsg}
        </div>
      )}

      <div className="row mt">
        <button className="btn" onClick={onSave} disabled={saving || saveMsg.startsWith('Saved')}>
          {saving ? <><span className="spinner" /> Saving…</> : 'Save to my profile'}
        </button>
        <button className="btn btn-ghost" onClick={onDone}>Go to dashboard</button>
      </div>
    </div>
  )
}
