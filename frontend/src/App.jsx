import { useCallback, useEffect, useRef, useState } from 'react'

import * as api from './api'
import { loadTheme, saveTheme } from './lib/themes'
import Composer from './components/Composer'
import Header from './components/Header'
import Message from './components/Message'
import ProfilePanel from './components/ProfilePanel'
import Welcome from './components/Welcome'

const SESSION_KEY = 'taste-agent:session'

export default function App() {
  const [health, setHealth] = useState(null)
  const [greeting, setGreeting] = useState('')
  const [sessionId, setSessionId] = useState(() => localStorage.getItem(SESSION_KEY))
  const [messages, setMessages] = useState([])
  const [profile, setProfile] = useState(null)
  const [coverage, setCoverage] = useState(null)
  const [tasteRead, setTasteRead] = useState(null)
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)
  const [panelOpen, setPanelOpen] = useState(false)
  const [theme, setTheme] = useState(loadTheme)

  const threadRef = useRef(null)

  useEffect(() => {
    saveTheme(theme)
  }, [theme])

  useEffect(() => {
    api.getHealth().then(setHealth).catch(() => {})
    api.getGreeting().then((r) => setGreeting(r.message)).catch(() => {})
  }, [])

  // Reload a session the browser already knows about.
  useEffect(() => {
    if (!sessionId) return
    api
      .getSession(sessionId)
      .then((session) => {
        setMessages(session.messages)
        setProfile(session.profile)
      })
      .catch((err) => {
        // Only forget the session if the server says it is really gone. A
        // restart or a dropped connection must not wipe someone's profile.
        if (err.status === 404) {
          localStorage.removeItem(SESSION_KEY)
          setSessionId(null)
        } else {
          setError('Backend unreachable - your session is safe, retrying on next message.')
        }
      })
  }, [sessionId])

  useEffect(() => {
    if (!sessionId) return
    api
      .getProfile(sessionId)
      .then((r) => {
        setProfile(r.profile)
        setCoverage(r.pillar_coverage)
      })
      .catch(() => {})
    api.getTasteRead(sessionId).then(setTasteRead).catch(() => {})
  }, [sessionId, messages])

  // Scroll the thread itself. scrollIntoView walks up to whichever ancestor it
  // thinks is scrollable, which is not this one once the page stops scrolling.
  useEffect(() => {
    const thread = threadRef.current
    if (!thread) return
    thread.scrollTo({ top: thread.scrollHeight, behavior: 'smooth' })
  }, [messages, busy])

  const send = useCallback(
    async (text) => {
      const body = (text ?? draft).trim()
      if (!body || busy) return

      setDraft('')
      setError(null)
      setBusy(true)
      // Show the message straight away; the server echoes it back on reply.
      setMessages((prev) => [...prev, { id: `local-${Date.now()}`, role: 'user', content: body }])

      try {
        const result = await api.sendMessage(sessionId, body)
        if (!sessionId) {
          localStorage.setItem(SESSION_KEY, result.session_id)
          setSessionId(result.session_id)
        }
        setMessages(result.session.messages)
        setProfile(result.session.profile)
      } catch (err) {
        setError(String(err.message || err))
      } finally {
        setBusy(false)
      }
    },
    [draft, busy, sessionId],
  )

  // Refresh the panel after an action that changes the profile but not the chat.
  async function refreshProfile() {
    const [p, read] = await Promise.all([
      api.getProfile(sessionId),
      api.getTasteRead(sessionId),
    ])
    setProfile(p.profile)
    setCoverage(p.pillar_coverage)
    setTasteRead(read)
  }

  async function dislike(entityId) {
    if (!sessionId) return
    try {
      await api.dislikeSignal(sessionId, entityId)
      await refreshProfile()
    } catch (err) {
      setError(String(err.message || err))
    }
  }

  async function removeSignal(entityId) {
    if (!sessionId) return
    try {
      await api.removeSignal(sessionId, entityId)
      await refreshProfile()
    } catch (err) {
      setError(String(err.message || err))
    }
  }

  function reset() {
    localStorage.removeItem(SESSION_KEY)
    setSessionId(null)
    setMessages([])
    setProfile(null)
    setCoverage(null)
    setTasteRead(null)
    setError(null)
  }

  return (
    <div className="aurora relative flex h-screen overflow-hidden text-neutral-100">
      <main className="relative z-10 flex min-w-0 flex-1 flex-col">
        <Header
          health={health}
          theme={theme}
          onTheme={setTheme}
          onReset={reset}
          onToggleProfile={() => setPanelOpen(true)}
        />

        <div ref={threadRef} className="flex-1 overflow-y-auto">
          <div className="mx-auto max-w-3xl space-y-5 px-5 py-6">
            {messages.length === 0 ? (
              <Welcome greeting={greeting} onPick={send} />
            ) : (
              messages.map((message) => (
                <Message key={message.id} message={message} onDislike={dislike} />
              ))
            )}

            {busy && <Thinking />}
            {error && (
              <p className="rounded-lg border border-red-900/50 bg-red-950/30 px-3 py-2 text-sm text-red-400">
                {error}
              </p>
            )}
          </div>
        </div>

        <Composer value={draft} onChange={setDraft} onSend={() => send()} busy={busy} />
      </main>

      <div className="relative z-10 hidden w-80 shrink-0 lg:block">
        <ProfilePanel
          profile={profile}
          coverage={coverage}
          tasteRead={tasteRead}
          onRemove={removeSignal}
          onAsk={send}
        />
      </div>

      {panelOpen && (
        <div className="fixed inset-0 z-20 flex lg:hidden">
          <button
            type="button"
            aria-label="Close profile"
            onClick={() => setPanelOpen(false)}
            className="flex-1 bg-black/60"
          />
          <div className="w-72 max-w-[85vw]">
            <ProfilePanel
              profile={profile}
              coverage={coverage}
              tasteRead={tasteRead}
              onRemove={removeSignal}
              onAsk={(text) => {
                setPanelOpen(false)
                send(text)
              }}
            />
          </div>
        </div>
      )}
    </div>
  )
}

function Thinking() {
  return (
    <div className="flex items-center gap-1.5 text-sm text-neutral-600">
      {[0, 150, 300].map((delay) => (
        <span
          key={delay}
          className="size-1.5 animate-pulse rounded-full bg-neutral-600"
          style={{ animationDelay: `${delay}ms` }}
        />
      ))}
    </div>
  )
}
