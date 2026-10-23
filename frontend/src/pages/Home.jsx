import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api'

export default function Home() {
  const [stats, setStats] = useState(null)
  const [tests, setTests] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    Promise.all([api.stats(), api.testTypes()])
      .then(([nextStats, nextTests]) => {
        setStats(nextStats)
        setTests(nextTests)
      })
      .catch((e) => setError(e.message))
  }, [])

  return (
    <div className="container page">
      {error && <div className="alert alert-error">{error}</div>}
      <div className="hero">
        <h1>Get scouted from <span>anywhere</span>.</h1>
        <p>
          Record a standard fitness test on your phone. Our AI analyses your
          form with real pose estimation, scores your performance, and puts
          you on regional and national leaderboards that scouts actually watch.
          No travel. No trials. No gatekeepers.
        </p>
        <div className="row" style={{ justifyContent: 'center' }}>
          <Link to="/signup" className="btn">Start your assessment</Link>
          <Link to="/leaderboard" className="btn btn-ghost">View leaderboards</Link>
        </div>
      </div>

      {stats && (
        <div className="grid grid-4 mb">
          <div className="card stat">
            <div className="stat-value">{stats.total_athletes}</div>
            <div className="stat-label">Athletes</div>
          </div>
          <div className="card stat">
            <div className="stat-value">{stats.total_assessments}</div>
            <div className="stat-label">Tests submitted</div>
          </div>
          <div className="card stat">
            <div className="stat-value">{stats.completed_assessments}</div>
            <div className="stat-label">AI scored</div>
          </div>
          <div className="card stat">
            <div className="stat-value">{stats.states_represented}</div>
            <div className="stat-label">States</div>
          </div>
        </div>
      )}

      <div className="grid grid-3 mb">
        <div className="card">
          <div className="card-title">1 · Record</div>
          <p className="muted">
            Film yourself doing any supported test with your phone camera.
            Side-on, full body in frame.
          </p>
        </div>
        <div className="card">
          <div className="card-title">2 · AI analyses</div>
          <p className="muted">
            MediaPipe pose estimation tracks 33 body landmarks per frame to
            count reps, measure joint angles and judge your form.
          </p>
        </div>
        <div className="card">
          <div className="card-title">3 · Get ranked</div>
          <p className="muted">
            Your best result appears on the leaderboard, filterable by state
            and district so regional talent gets seen.
          </p>
        </div>
      </div>

      <div className="card">
        <div className="card-title">Supported tests ({tests.length})</div>
        <div className="grid grid-4">
          {tests.map((t) => (
            <div key={t.key} style={{ padding: '10px 0' }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{t.display_name}</div>
              <div className="muted">
                {t.type.replace('_', ' ')} · {t.unit}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
