import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'
import { useAuth } from '../auth.jsx'

const badgeFor = (s) =>
  s === 'completed' ? 'badge-ok'
  : s === 'flagged' ? 'badge-warn'
  : s === 'failed' || s === 'rejected' ? 'badge-err'
  : 'badge-run'

const sourceLabel = (source) => ({
  demo_seed: 'sample data',
  live_camera: 'live camera',
  local_video: 'local video',
  uploaded_video: 'uploaded video',
}[source])

export default function Dashboard() {
  const { user } = useAuth()
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [open, setOpen] = useState(null)

  const load = () => {
    setLoading(true)
    setError('')
    api.myAssessments()
      .then(setItems)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }
  useEffect(load, [])

  const remove = async (id) => {
    await api.deleteAssessment(id)
    setItems((xs) => xs.filter((x) => x.id !== id))
  }

  const done = items.filter((i) => i.status === 'completed')
  const best = done.reduce((acc, i) => {
    if (!acc[i.test_type] || i.score > acc[i.test_type].score) acc[i.test_type] = i
    return acc
  }, {})

  return (
    <div className="container page">
      <div className="spread mb">
        <div>
          <h1 className="h1">Hi, {user?.name?.split(' ')[0]}</h1>
          <p className="sub" style={{ marginBottom: 0 }}>
            {user?.state ? `${user.district ? user.district + ', ' : ''}${user.state}` : 'Your assessments'}
          </p>
        </div>
        <Link to="/upload" className="btn">New test</Link>
      </div>

      <div className="grid grid-4 mb">
        <div className="card stat">
          <div className="stat-value">{items.length}</div>
          <div className="stat-label">Submitted</div>
        </div>
        <div className="card stat">
          <div className="stat-value">{done.length}</div>
          <div className="stat-label">Scored</div>
        </div>
        <div className="card stat">
          <div className="stat-value">{Object.keys(best).length}</div>
          <div className="stat-label">Tests tried</div>
        </div>
        <div className="card stat">
          <div className="stat-value">
            {done.length
              ? Math.round(done.reduce((s, i) => s + (i.ai_result?.scores?.overall_score || 0), 0) / done.length)
              : '—'}
          </div>
          <div className="stat-label">Avg overall</div>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Your submissions</div>
        {error && <div className="alert alert-error">{error}</div>}
        {loading ? (
          <div className="empty"><span className="spinner" /></div>
        ) : items.length === 0 ? (
          <div className="empty">
            No tests yet.<br />
            <Link to="/upload" className="btn mt">Submit your first test</Link>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Test</th><th>Score</th><th>Overall</th><th>Status</th>
                  <th>Date</th><th></th>
                </tr>
              </thead>
              <tbody>
                {items.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <b>{a.ai_result?.display_name || a.test_type}</b>
                      {sourceLabel(a.ai_result?.source) && (
                        <div className="muted">{sourceLabel(a.ai_result.source)}</div>
                      )}
                    </td>
                    <td>{a.score != null ? `${a.score} ${a.unit || ''}` : '—'}</td>
                    <td>{a.ai_result?.scores?.overall_score ?? '—'}</td>
                    <td><span className={`badge ${badgeFor(a.status)}`}>{a.status}</span></td>
                    <td className="muted">
                      {a.submitted_at ? new Date(a.submitted_at).toLocaleDateString() : '—'}
                    </td>
                    <td>
                      <div className="row">
                        {a.ai_result && (
                          <button className="btn btn-ghost btn-sm"
                                  onClick={() => setOpen(open === a.id ? null : a.id)}>
                            {open === a.id ? 'Hide' : 'Details'}
                          </button>
                        )}
                        <button className="btn btn-danger btn-sm" onClick={() => remove(a.id)}>
                          Delete
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {open && (() => {
        const a = items.find((x) => x.id === open)
        const r = a?.ai_result || {}
        const s = r.scores || {}
        return (
          <div className="card mt">
            <div className="card-title">{r.display_name || a.test_type} — breakdown</div>
            <div className="grid grid-4 mb">
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
            <div className="grid grid-4 mb">
              <div><div className="muted">Reps</div><b>{r.reps ?? 0}</b></div>
              <div><div className="muted">Bad form</div><b>{r.bad_form_reps ?? 0}</b></div>
              <div><div className="muted">Duration</div><b>{r.duration_sec ?? 0}s</b></div>
              <div><div className="muted">Coverage</div><b>{Math.round((r.pose_coverage ?? 0) * 100)}%</b></div>
            </div>
            {(r.suggestions || []).map((t, i) => (
              <div key={i} className="muted" style={{ marginBottom: 6 }}>• {t}</div>
            ))}
          </div>
        )
      })()}
    </div>
  )
}
