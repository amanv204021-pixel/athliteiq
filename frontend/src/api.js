// Requests default to relative URLs; set VITE_API_BASE_URL only for a separate API origin.

const TOKEN_KEY = 'athleteiq_token'
const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || '').replace(/\/+$/, '')

export const getToken = () => localStorage.getItem(TOKEN_KEY)
export const setToken = (t) => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = () => localStorage.removeItem(TOKEN_KEY)

async function fetchApi(path, options, timeoutMs = 30000) {
  const controller = new AbortController()
  const timeout = setTimeout(() => controller.abort(), timeoutMs)
  try {
    return await fetch(`${API_BASE_URL}${path}`, {
      ...options,
      signal: controller.signal,
    })
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('The request timed out. Check the server and try again.')
    }
    if (error instanceof TypeError) {
      throw new Error('Could not reach the AthliteIQ API. Check that the backend is running.')
    }
    throw error
  } finally {
    clearTimeout(timeout)
  }
}

async function responseData(res) {
  const text = await res.text()
  if (!text) return null
  try {
    return JSON.parse(text)
  } catch {
    if (res.ok) throw new Error('The API returned an invalid response.')
    return null
  }
}

async function request(path, {
  method = 'GET', body, form, auth = true, timeoutMs = 30000,
} = {}) {
  const headers = {}
  if (auth && getToken()) headers.Authorization = `Bearer ${getToken()}`

  let payload
  if (form) {
    payload = form // FormData: let the browser set the boundary
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json'
    payload = JSON.stringify(body)
  }

  const res = await fetchApi(path, { method, headers, body: payload }, timeoutMs)

  if (res.status === 204) return null
  const data = await responseData(res)

  if (!res.ok) {
    const detail = data?.detail
    const msg = Array.isArray(detail)
      ? detail.map((d) => `${d.loc?.slice(-1)[0]}: ${d.msg}`).join(', ')
      : detail || `Request failed (${res.status})`
    const err = new Error(msg)
    err.status = res.status
    throw err
  }
  return data
}

export const api = {
  health: () => request('/api/health', { auth: false }),
  frontendStatus: () => request('/api/frontend-status', { auth: false }),
  stats: () => request('/api/stats', { auth: false }),
  testTypes: () => request('/api/test-types', { auth: false }),

  signup: (payload) => request('/api/auth/signup', { method: 'POST', body: payload, auth: false }),
  login: async (email, password) => {
    // OAuth2PasswordRequestForm expects form-encoded username/password
    const fd = new URLSearchParams()
    fd.append('username', email)
    fd.append('password', password)
    const res = await fetchApi('/api/auth/login', { method: 'POST', body: fd })
    const data = await responseData(res)
    if (!res.ok) throw new Error(data?.detail || `Login failed (${res.status})`)
    return data
  },
  me: () => request('/api/auth/me'),

  myAssessments: () => request('/api/assessments/me'),
  getAssessment: (id) => request(`/api/assessments/${id}`),
  deleteAssessment: (id) => request(`/api/assessments/${id}`, { method: 'DELETE' }),
  submitLive: (testType, payload) =>
    request('/api/assessments/live', {
      method: 'POST',
      body: { ...payload, test_type: testType },
    }),

  upload: (testType, file) => {
    const fd = new FormData()
    fd.append('test_type', testType)
    fd.append('file', file)
    return request('/api/assessments/upload', {
      method: 'POST',
      form: fd,
      timeoutMs: 180000,
    })
  },

  leaderboard: (params) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null)
    )
    return request(`/api/leaderboard?${qs}`, { auth: false })
  },
  states: () => request('/api/leaderboard/states', { auth: false }),

  athletes: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== '' && v != null)
    )
    return request(`/api/scouts/athletes?${qs}`)
  },
  athleteAssessments: (id) => request(`/api/scouts/athletes/${id}/assessments`),
  flagged: () => request('/api/scouts/flagged'),
  review: (id, approve) =>
    request(`/api/scouts/assessments/${id}/review?approve=${approve}`, { method: 'POST' }),
}
