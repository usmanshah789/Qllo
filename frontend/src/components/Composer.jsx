export default function Composer({ value, onChange, onSend, busy }) {
  function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSend()
    }
  }

  return (
    <div className="relative z-10 p-4">
      <div className="panel mx-auto flex max-w-3xl items-end gap-2 rounded-2xl p-2 focus-within:border-white/20">
        <textarea
          rows={1}
          value={value}
          disabled={busy}
          placeholder="Name something you love…"
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          className="max-h-40 flex-1 resize-none bg-transparent px-2 py-1.5 text-sm text-neutral-100 placeholder:text-neutral-600 focus:outline-none disabled:opacity-50"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={busy || !value.trim()}
          className="accent-fill shrink-0 rounded-xl px-4 py-2 text-sm font-medium text-neutral-950 transition-opacity disabled:opacity-30"
        >
          {busy ? '…' : 'Send'}
        </button>
      </div>
      <p className="mx-auto mt-2 max-w-3xl px-1 text-[11px] text-neutral-600">
        Enter to send · Shift+Enter for a new line
      </p>
    </div>
  )
}
