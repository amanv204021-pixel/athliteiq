import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth.jsx'

const STATES = [
  'Andhra Pradesh', 'Assam', 'Bihar', 'Chhattisgarh', 'Delhi', 'Goa', 'Gujarat',
  'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka', 'Kerala',
  'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Odisha', 'Punjab', 'Rajasthan',
  'Tamil Nadu', 'Telangana', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
]

export default function Signup() {
  const { signup } = useAuth()
  const nav = useNavigate()
  const [f, setF] = useState({
    name: '', email: '', password: '', age: '', gender: '',
    state: '', district: '', role: 'athlete',
  })
  const [err, setErr] = useState('')
  const [busy, setBusy] = useState(false)

  const set = (k) => (e) => setF({ ...f, [k]: e.target.value })

  const submit = async (e) => {
    e.preventDefault()
    setErr(''); setBusy(true)
    try {
      const payload = { ...f, age: f.age ? Number(f.age) : null }
      Object.keys(payload).forEach((k) => { if (payload[k] === '') payload[k] = null })
      payload.role = f.role
      const u = await signup(payload)
      nav(u?.role === 'scout' ? '/scout' : '/dashboard')
    } catch (e2) {
      setErr(e2.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="container page" style={{ maxWidth: 560 }}>
      <h1 className="h1">Create your profile</h1>
      <p className="sub">Athletes get scored and ranked. Scouts get to browse talent.</p>
      <form className="card" onSubmit={submit}>
        {err && <div className="alert alert-error">{err}</div>}

        <label>I am a…</label>
        <select value={f.role} onChange={set('role')}>
          <option value="athlete">Athlete</option>
          <option value="scout">Scout / Coach</option>
        </select>

        <label>Full name</label>
        <input value={f.name} required onChange={set('name')} placeholder="Aryan Kumar" />

        <label>Email</label>
        <input type="email" value={f.email} required onChange={set('email')} placeholder="you@example.com" />

        <label>Password (min 6 characters)</label>
        <input type="password" value={f.password} required minLength={6}
               onChange={set('password')} placeholder="••••••••" />

        {f.role === 'athlete' && (
          <div className="grid grid-2">
            <div>
              <label>Age</label>
              <input type="number" value={f.age} min={5} max={100} onChange={set('age')} placeholder="19" />
            </div>
            <div>
              <label>Gender</label>
              <select value={f.gender} onChange={set('gender')}>
                <option value="">Prefer not to say</option>
                <option value="male">Male</option>
                <option value="female">Female</option>
                <option value="other">Other</option>
              </select>
            </div>
            <div>
              <label>State</label>
              <select value={f.state} onChange={set('state')}>
                <option value="">Select state</option>
                {STATES.map((s) => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label>District</label>
              <input value={f.district} onChange={set('district')} placeholder="Patna" />
            </div>
          </div>
        )}

        <button className="btn btn-full" disabled={busy}>
          {busy ? <><span className="spinner" /> Creating…</> : 'Create account'}
        </button>
        <p className="muted mt" style={{ textAlign: 'center' }}>
          Already registered? <Link to="/login" style={{ color: 'var(--accent-2)' }}>Log in</Link>
        </p>
      </form>
    </div>
  )
}
