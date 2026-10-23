import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'

export default function Upload() {
  const nav = useNavigate()
  const fileRef = useRef(null)
  const [tests, setTests] = useState([])
  const [testType, setTestType] = useState('squat')
  const [file, setFile] = useState(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [result, setResult] = useState(null)

  useEffect(() => { api.testTypes().then(setTests).catch(() => {}) }, [])

  const submit = async (e) => {
    e.preventDefault()
    if (!file) { setErr('Choose a video file first.'); return }
    setErr(''); setBusy(true); setResult(null)
    try {
      const created = await api.upload(testType, file)
      // Analysis runs as a background task; poll until it settles.
      let a = created
      for (let i = 0; i < 40 && a.status === 'processing'; i++) {
        await new Promise((r) => setTimeout(r, 1000))
        a = await api.getAssessment(created.id)
      }
      setResult(a)
    } catch (e2) {
      setErr(e2.message)
    } finally {
      setBusy(false)
    }
  }

  const chosen = tests.find((t) => t.key === testType)

  return (
    <div className="container page" style={{ maxWidth: 680 }}>
      <h1 className="h1">Submit a test</h1>
      <p className="sub">
        Film side-on with your whole body in frame, in good light. MP4, MOV,
        AVI, MKV or WebM, up to 80 MB.
      </p>

      <form className="card" onSubmit={submit}>
        {err && <div className="alert alert-error">{err}</div>}

        <label>Test type</label>
        <select value={testType} onChange={(e) => setTestType(e.target.value)}>
          {tests.map((t) => (
            <option key={t.key} value={t.key}>{t.display_name}</option>
          ))}
        </select>
        {chosen && (
          <p className="muted" style={{ marginTop: 6 }}>
            Measured in <b>{chosen.unit}</b> · {chosen.type.replace('_', ' ')}
          </p>
        )}

        <label>Video file</label>
        <div
          className="drop"
          onClick={() => fileRef.current?.click()}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => {
            e.preventDefault()
            const dropped = e.dataTransfer.files?.[0]
            if (dropped) {
              setFile(dropped)
              setErr('')
            }
          }}
        >
          {file ? (
            <>
              <div style={{ fontWeight: 600 }}>{file.name}</div>
              <div className="muted">{(file.size / 1048576).toFixed(1)} MB · click to change</div>
            </>
          ) : (
            <>
              <div style={{ fontWeight: 600 }}>Click to choose a video</div>
              <div className="muted">or drag one onto this box</div>
            </>
          )}
        </div>
        <input
          ref={fileRef} type="file" accept="video/*" style={{ display: 'none' }}
          onChange={(e) => { setFile(e.target.files?.[0] || null); setErr('') }}
        />

        <button className="btn btn-full" disabled={busy || !file}>
          {busy ? <><span className="spinner" /> Analysing…</> : 'Upload & analyse'}
        </button>
        {busy && (
          <p className="muted mt" style={{ textAlign: 'center' }}>
            Running pose estimation frame by frame — this can take a moment.
          </p>
        )}
      </form>

      {result && <ResultCard a={result} onDone={() => nav('/dashboard')} />}
    </div>
  )
}

function ResultCard({ a, onDone }) {
  const r = a.ai_result || {}
  const s = r.scores || {}

  if (a.status === 'failed') {
    return (
      <div className="card mt">
        <div className="alert alert-error">
          <b>Analysis failed.</b> {a.error_message || 'Unknown error'}
        </div>
        <button className="btn btn-ghost" onClick={onDone}>Back to dashboard</button>
      </div>
    )
  }

  return (
    <div className="card mt">
      <div className="spread mb">
        <div className="card-title" style={{ margin: 0 }}>{r.display_name || a.test_type}</div>
        <span className={`badge ${a.status === 'flagged' ? 'badge-warn' : 'badge-ok'}`}>
          {a.status}
        </span>
      </div>

      <div style={{ fontSize: 40, fontWeight: 900, letterSpacing: -1.5 }}>
        {a.score}<span style={{ fontSize: 16, color: 'var(--muted)' }}> {a.unit}</span>
      </div>

      {a.status === 'flagged' && (
        <div className="alert alert-info">
          Flagged for review: {(r.cheat_flags || []).join(', ').replace(/_/g, ' ')}.
          A scout will verify this submission before it reaches the leaderboard.
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

      <div className="grid grid-3 mt">
        <div><div className="muted">Reps</div><b>{r.reps ?? 0}</b></div>
        <div><div className="muted">Duration</div><b>{r.duration_sec ?? 0}s</b></div>
        <div><div className="muted">Pose coverage</div><b>{Math.round((r.pose_coverage ?? 0) * 100)}%</b></div>
      </div>

      {(r.suggestions || []).length > 0 && (
        <>
          <div className="card-title mt">Coach feedback</div>
          <ul style={{ paddingLeft: 18 }}>
            {r.suggestions.map((t, i) => (
              <li key={i} className="muted" style={{ marginBottom: 6 }}>{t}</li>
            ))}
          </ul>
        </>
      )}

      <button className="btn btn-ghost mt" onClick={onDone}>Go to dashboard</button>
    </div>
  )
}
