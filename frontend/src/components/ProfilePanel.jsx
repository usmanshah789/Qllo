import { useState } from 'react'

import { PILLARS } from '../lib/pillars'
import TasteRead from './TasteRead'

export default function ProfilePanel({ profile, coverage, tasteRead, onRemove, onAsk }) {
  const signals = profile?.entities ?? []
  const likes = signals.filter((s) => s.sentiment === 'like')
  const dislikes = signals.filter((s) => s.sentiment === 'dislike')

  return (
    <aside className="flex h-full w-full flex-col gap-7 overflow-y-auto border-l border-white/8 bg-black/30 p-5 backdrop-blur">
      <section>
        <Label>Taste read</Label>
        <TasteRead read={tasteRead} />
        {tasteRead?.ready && likes.length > 0 && (
          <CopyTaste read={tasteRead} likes={likes} location={profile?.location} />
        )}
      </section>

      <section>
        <Label>Signals</Label>
        {likes.length === 0 ? (
          <p className="mt-3 text-sm text-neutral-600">
            Nothing yet. Name a film, a brand, a place — anything you love.
          </p>
        ) : (
          <ul className="mt-2 space-y-0.5">
            {likes.map((signal) => (
              <SignalRow key={signal.id} signal={signal} onRemove={onRemove} />
            ))}
          </ul>
        )}
      </section>

      <section>
        <Label>Pillars</Label>
        <ul className="mt-2 space-y-0.5">
          {PILLARS.map((pillar) => {
            const count = coverage?.[pillar.key] ?? 0
            return (
              <li key={pillar.key}>
                <button
                  type="button"
                  onClick={() => onAsk(pillar.ask)}
                  title={pillar.ask}
                  className="flex w-full items-center gap-2.5 rounded-lg px-2 py-1.5 text-left text-sm transition-colors hover:bg-white/5"
                >
                  <span
                    className={`size-1.5 shrink-0 rounded-full ${count ? pillar.dot : 'bg-white/15'}`}
                  />
                  <span className={count ? 'text-neutral-200' : 'text-neutral-600'}>
                    {pillar.label}
                  </span>
                  <span className="ml-auto tabular-nums text-xs text-neutral-600">
                    {count || '—'}
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>

      {profile?.location && (
        <section>
          <Label>Anchored in</Label>
          <p className="mt-2 flex items-center gap-1.5 text-sm text-neutral-200">
            <span className="text-neutral-600">◎</span>
            {profile.location}
          </p>
        </section>
      )}

      {dislikes.length > 0 && (
        <section>
          <Label>Ruled out</Label>
          <ul className="mt-2 space-y-1 text-sm text-neutral-600">
            {dislikes.map((signal) => (
              <li key={signal.id} className="truncate line-through decoration-white/20">
                {signal.name}
              </li>
            ))}
          </ul>
        </section>
      )}
    </aside>
  )
}

function Label({ children }) {
  return (
    <div>
      <h2 className="text-[11px] font-medium uppercase tracking-wider text-neutral-500">
        {children}
      </h2>
      <div className="accent-rule mt-1.5 h-px w-8 opacity-80" />
    </div>
  )
}

// A taste profile is the kind of thing people want to paste to a friend.
function CopyTaste({ read, likes, location }) {
  const [copied, setCopied] = useState(false)

  async function copy() {
    const lines = [
      'My taste, read by Qloo:',
      read.signature.map((t) => t.name).join(' · '),
      '',
      'Built from: ' + likes.map((s) => s.name).join(', '),
      location ? `Around ${location}` : null,
    ].filter(Boolean)

    try {
      await navigator.clipboard.writeText(lines.join('\n'))
      setCopied(true)
      setTimeout(() => setCopied(false), 1600)
    } catch {
      // Clipboard is blocked in some browsers; silently leave the button alone.
    }
  }

  return (
    <button
      type="button"
      onClick={copy}
      className="mt-3 w-full rounded-lg border border-white/10 px-3 py-1.5 text-xs text-neutral-400 transition-colors hover:bg-white/5 hover:text-neutral-200"
    >
      {copied ? 'Copied' : 'Copy my taste read'}
    </button>
  )
}

function SignalRow({ signal, onRemove }) {
  return (
    <li className="group flex items-center gap-2 rounded-lg px-2 py-1.5 transition-colors hover:bg-white/5">
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm text-neutral-200">{signal.name}</p>
        <p className="text-xs text-neutral-600">{signal.type_label}</p>
      </div>
      <button
        type="button"
        onClick={() => onRemove(signal.id)}
        title="Remove"
        className="shrink-0 rounded px-1 text-neutral-700 opacity-0 transition-opacity hover:text-neutral-400 group-hover:opacity-100"
      >
        ×
      </button>
    </li>
  )
}
