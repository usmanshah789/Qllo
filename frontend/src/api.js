const JSON_HEADERS = { 'Content-Type': 'application/json' }

// Empty in development, where Vite proxies /api to the local backend. In
// production this is the deployed API's origin. Render hands over a bare
// hostname, so add the scheme if it is missing.
function apiBase() {
  const raw = (import.meta.env.VITE_API_URL ?? '').trim().replace(/\/$/, '')
  if (!raw) return ''
  return /^https?:\/\//.test(raw) ? raw : `https://${raw}`
}

const BASE = apiBase()

const url = (path) => `${BASE}${path}`

class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

async function request(path, options) {
  const res = await fetch(path, options)
  if (!res.ok) {
    const body = await res.text()
    throw new ApiError(body.slice(0, 200) || `${res.status} ${res.statusText}`, res.status)
  }
  return res.json()
}

export const getHealth = () => request(url('/api/health'))

export const getGreeting = () => request(url('/api/chat/greeting'))

export const getProfile = (sessionId) =>
  request(url(`/api/sessions/${sessionId}/profile`))

export const getSession = (sessionId) => request(url(`/api/sessions/${sessionId}`))

export const sendMessage = (sessionId, message) =>
  request(url('/api/chat'), {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ session_id: sessionId, message }),
  })

export const addSignal = (sessionId, query) =>
  request(url(`/api/sessions/${sessionId}/signals`), {
    method: 'POST',
    headers: JSON_HEADERS,
    body: JSON.stringify({ query }),
  })

export const getTasteRead = (sessionId) =>
  request(url(`/api/sessions/${sessionId}/taste-read`))

export const dislikeSignal = (sessionId, entityId) =>
  request(url(`/api/sessions/${sessionId}/signals/${encodeURIComponent(entityId)}/dislike`), {
    method: 'POST',
  })

export const removeSignal = (sessionId, entityId) =>
  request(url(`/api/sessions/${sessionId}/signals/${encodeURIComponent(entityId)}`), {
    method: 'DELETE',
  })
