import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'

export default function Login() {
  const { login } = useAuth()
  const nav = useNavigate()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      const u = await login(email, password)
      nav(u?.role === 'scout' ? '/scout' : '/dashboard')
    } catch (e2) {
      setErr(e2.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-page">
      <section className="login-intro" aria-labelledby="login-brand">
        <img className="login-wordmark" src="/athliteiq-wordmark.png" alt="AthliteIQ" />
        <h1 id="login-brand" className="login-brand-title">Your effort deserves to be seen.</h1>
        <p className="login-quote">
          “Every rep is a step closer to your next personal best.”
        </p>
        <a className="login-scroll-link" href="#login-form">
          Scroll to log in <span aria-hidden="true">↓</span>
        </a>
      </section>

      <section className="login-form-section" id="login-form" aria-labelledby="login-title">
        <div className="login-form-wrap">
          <h2 id="login-title" className="h1">Welcome back</h2>
          <p className="sub">Log in to see your results and ranking.</p>
          <form className="card" onSubmit={submit}>
            {err && <div className="alert alert-error">{err}</div>}
            <label htmlFor="login-email">Email</label>
            <input id="login-email" type="email" value={email} required autoComplete="email"
                   onChange={(e) => setEmail(e.target.value)} placeholder="you@example.com" />
            <label htmlFor="login-password">Password</label>
            <input id="login-password" type="password" value={password} required
                   autoComplete="current-password" onChange={(e) => setPassword(e.target.value)}
                   placeholder="••••••••" />
            <button className="btn btn-full" disabled={busy}>
              {busy ? <><span className="spinner" /> Logging in…</> : 'Log in'}
            </button>
            <p className="muted mt" style={{ textAlign: 'center' }}>
              No account? <Link to="/signup" style={{ color: 'var(--accent-2)' }}>Sign up</Link>
            </p>
          </form>
        </div>
      </section>
    </main>
  )
}
