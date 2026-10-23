import { createContext, useContext, useEffect, useState } from 'react'
import { api, clearToken, getToken, setToken } from './api'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  // Restore the session on load if a token is already stored.
  useEffect(() => {
    if (!getToken()) { setLoading(false); return }
    api.me()
      .then(setUser)
      .catch(() => clearToken())
      .finally(() => setLoading(false))
  }, [])

  const login = async (email, password) => {
    const data = await api.login(email, password)
    setToken(data.access_token)
    setUser(data.user ?? (await api.me()))
    return data.user
  }

  const signup = async (payload) => {
    const data = await api.signup(payload)
    setToken(data.access_token)
    setUser(data.user ?? (await api.me()))
    return data.user
  }

  const logout = () => { clearToken(); setUser(null) }

  return (
    <AuthCtx.Provider value={{ user, loading, login, signup, logout }}>
      {children}
    </AuthCtx.Provider>
  )
}
