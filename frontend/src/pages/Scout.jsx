import { useEffect, useState } from 'react'
import { api } from '../api'

export default function Scout() {
  const [tab, setTab] = useState('athletes')
  const [athletes, setAthletes] = useState([])
  const [flagged, setFlagged] = useState([])
  const [search, setSearch] = useState('')
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(true)

  const loadAthletes = () => {
    setLoading(true)
    api.athletes({ search }).then(setAthletes).catch(() => {}).finally(() => setLoading(false))
  }
  const loadFlagged = () => {
    setLoading(true)
    api.flagged().then(setFlagged).catch(() => {}).finally(() => setLoading(false))
  }

  useEffect(() => { tab === 'athletes' ? loadAthletes() : loadFlagged() }, [tab])

  const openAthlete = async (a) => {
    const rows = await api.athleteAssessments(a.id)
    setDetail({ athlete: a, rows })
  }

  const review = async (id, approve) => {
    await api.review(id, approve)
    loadFlagged()
  }

  return (
    <div className="container page">
      <h1 className="h1">Scout portal</h1>
      <p className="sub">Browse verified athletes and review flagged submissions.</p>

      <div className="row mb">
        <button className={`btn ${tab === 'athletes' ? '' : 'btn-ghost'}`}
                onClick={() => setTab('athletes')}>Athletes</button>
        <button className={`btn ${tab === 'flagged' ? '' : 'btn-ghost'}`}
                onClick={() => setTab('flagged')}>
          Review queue {flagged.length ? `(${flagged.length})` : ''}
        </button>
      </div>

      {tab === 'athletes' && (
        <div className="card">
          <div className="row mb">
            <input placeholder="Search by name…" value={search}
                   onChange={(e) => setSearch(e.target.value)}
                   onKeyDown={(e) => e.key === 'Enter' && loadAthletes()} />
            <button className="btn btn-ghost" onClick={loadAthletes}>Search</button>
          </div>
          {loading ? <div className="empty"><span className="spinner" /></div>
            : athletes.length === 0 ? <div className="empty">No athletes registered yet.</div>
            : (
              <table>
                <thead><tr><th>Name</th><th className="hide-sm">Region</th><th className="hide-sm">Age</th><th></th></tr></thead>
                <tbody>
                  {athletes.map((a) => (
                    <tr key={a.id}>
                      <td><b>{a.name}</b><div className="muted">{a.email}</div></td>
                      <td className="muted hide-sm">{[a.district, a.state].filter(Boolean).join(', ') || '—'}</td>
                      <td className="muted hide-sm">{a.age ?? '—'}</td>
                      <td>
                        <button className="btn btn-ghost btn-sm" onClick={() => openAthlete(a)}>
                          View tests
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {tab === 'flagged' && (
        <div className="card">
          {loading ? <div className="empty"><span className="spinner" /></div>
            : flagged.length === 0 ? <div className="empty">Nothing to review. All clear.</div>
            : (
              <table>
                <thead><tr><th>Athlete</th><th>Test</th><th>Source</th><th>Score</th><th>Flags</th><th></th></tr></thead>
                <tbody>
                  {flagged.map((a) => (
                    <tr key={a.id}>
                      <td><b>{a.athlete_name}</b><div className="muted">{a.athlete_state}</div></td>
                      <td>{a.ai_result?.display_name || a.test_type}</td>
                      <td>
                        {a.ai_result?.source === 'demo_seed'
                          ? <span className="badge badge-warn">sample data</span>
                          : a.ai_result?.source?.replace(/_/g, ' ') || '—'}
                      </td>
                      <td>{a.score} <span className="muted">{a.unit}</span></td>
                      <td className="muted">
                        {(a.ai_result?.cheat_flags || []).join(', ').replace(/_/g, ' ') || '—'}
                      </td>
                      <td>
                        <div className="row">
                          <button className="btn btn-sm" onClick={() => review(a.id, true)}>Approve</button>
                          <button className="btn btn-danger btn-sm" onClick={() => review(a.id, false)}>Reject</button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
        </div>
      )}

      {detail && (
        <div className="card mt">
          <div className="spread mb">
            <div className="card-title" style={{ margin: 0 }}>
              {detail.athlete.name} — {detail.rows.length} submission(s)
            </div>
            <button className="btn btn-ghost btn-sm" onClick={() => setDetail(null)}>Close</button>
          </div>
          {detail.rows.length === 0 ? (
            <div className="empty">This athlete hasn't submitted any tests yet.</div>
          ) : (
            <table>
              <thead><tr><th>Test</th><th>Source</th><th>Score</th><th>Overall</th><th>Status</th></tr></thead>
              <tbody>
                {detail.rows.map((r) => (
                  <tr key={r.id}>
                    <td>{r.ai_result?.display_name || r.test_type}</td>
                    <td>
                      {r.ai_result?.source === 'demo_seed'
                        ? <span className="badge badge-warn">sample data</span>
                        : r.ai_result?.source?.replace(/_/g, ' ') || '—'}
                    </td>
                    <td>{r.score != null ? `${r.score} ${r.unit || ''}` : '—'}</td>
                    <td>{r.ai_result?.scores?.overall_score ?? '—'}</td>
                    <td><span className="badge badge-run">{r.status}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  )
}
