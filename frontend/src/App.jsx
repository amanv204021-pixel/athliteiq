import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth.jsx'
import Home from './pages/Home.jsx'
import Login from './pages/Login.jsx'
import Signup from './pages/Signup.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Upload from './pages/Upload.jsx'
import Live from './pages/Live.jsx'
import Leaderboard from './pages/Leaderboard.jsx'
import Scout from './pages/Scout.jsx'

function Protected({ children, role }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="container page"><span className="spinner" /></div>
  if (!user) return <Navigate to="/login" replace />
  if (role && user.role !== role && user.role !== 'admin')
    return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  const { user, logout } = useAuth()
  const isScout = user && (user.role === 'scout' || user.role === 'admin')

  return (
    <>
      <nav className="nav">
        <div className="container nav-inner">
          <NavLink to="/" className="brand" aria-label="AthliteIQ home">
            <img className="brand-wordmark" src="/athliteiq-wordmark.png" alt="AthliteIQ" />
          </NavLink>
          <div className="nav-links">
            <NavLink to="/leaderboard" className="nav-link">Leaderboard</NavLink>
            {user && <NavLink to="/dashboard" className="nav-link">Dashboard</NavLink>}
            {user && !isScout && <NavLink to="/live" className="nav-link">Live Test</NavLink>}
            {user && !isScout && <NavLink to="/upload" className="nav-link">Upload Video</NavLink>}
            {isScout && <NavLink to="/scout" className="nav-link">Scout Portal</NavLink>}
          </div>
          {user ? (
            <div className="row">
              <span className="muted hide-sm">{user.name}</span>
              <button className="btn btn-ghost btn-sm" onClick={logout}>Log out</button>
            </div>
          ) : (
            <div className="row">
              <NavLink to="/login" className="btn btn-ghost btn-sm">Log in</NavLink>
              <NavLink to="/signup" className="btn btn-sm">Sign up</NavLink>
            </div>
          )}
        </div>
      </nav>

      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/login" element={<Login />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/leaderboard" element={<Leaderboard />} />
        <Route path="/dashboard" element={<Protected><Dashboard /></Protected>} />
        <Route path="/upload" element={<Protected><Upload /></Protected>} />
        <Route path="/live" element={<Protected><Live /></Protected>} />
        <Route path="/scout" element={<Protected role="scout"><Scout /></Protected>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </>
  )
}
