import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Leaderboard() {
  const [tests, setTests] = useState([])
  const [states, setStates] = useState([])
  const [f, setF] = useState({ test_type: 'squat', state: '', gender: '', min_age: '', max_age: '' })
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  useEffect(() => {
    api.testTypes().then(setTests).catch(() => {})
    api.states().then(setStates).catch(() => {})
  }, [])

  useEffect(() => {
    setLoading(true); setErr('')
    api.leaderboard(f)
      .then(setRows)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false))
  }, [f])

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })
  const chosen = tests.find((t) => t.key === f.test_type)

  return (
    <div className="container page">
      <h1 className="h1">Leaderboard</h1>
      <p className="sub">
        Personal bests only — one entry per athlete. Filter by region to find
        talent wherever it is.
      </p>

      <div className="card mb">
        <div className="grid grid-4">
          <div>
            <label>Test</label>
            <select value={f.test_type} onChange={set('test_type')}>
              {tests.map((t) => <option key={t.key} value={t.key}>{t.display_name}</option>)}
            </select>
          </div>
          <div>
            <label>State</label>
            <select value={f.state} onChange={set('state')}>
              <option value="">All states</option>
              {states.map((s) => <option key={s} value={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label>Gender</label>
            <select value={f.gender} onChange={set('gender')}>
              <option value="">Any</option>
              <option value="male">Male</option>
              <option value="female">Female</option>
              <option value="other">Other</option>
            </select>
          </div>
          <div>
            <label>Age range</label>
            <div className="row">
              <input type="number" placeholder="Min" value={f.min_age} onChange={set('min_age')} />
              <input type="number" placeholder="Max" value={f.max_age} onChange={set('max_age')} />
            </div>
          </div>
        </div>
        {chosen && (
          <p className="muted mt">
            Ranked by {chosen.unit} — {chosen.higher_is_better ? 'higher' : 'lower'} is better.
          </p>
        )}
      </div>

      <div className="card">
        {err && <div className="alert alert-error">{err}</div>}
        {loading ? (
          <div className="empty"><span className="spinner" /></div>
        ) : rows.length === 0 ? (
          <div className="empty">
            No ranked results for this filter yet.<br />
            <span className="muted">Submitted tests appear here once the AI has scored them.</span>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>#</th><th>Athlete</th><th className="hide-sm">Region</th>
                  <th className="hide-sm">Age</th><th>Score</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.assessment_id}>
                    <td className={`rank rank-${r.rank}`}>{r.rank}</td>
                    <td><b>{r.name}</b></td>
                    <td className="muted hide-sm">
                      {[r.district, r.state].filter(Boolean).join(', ') || '—'}
                    </td>
                    <td className="muted hide-sm">{r.age ?? '—'}</td>
                    <td>
                      <b>{r.score}</b> <span className="muted">{r.unit}</span>
                      {r.source === 'demo_seed' && <div className="muted">sample data</div>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
