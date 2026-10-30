import ThemeSwitcher from './ThemeSwitcher'

export default function Header({ health, theme, onTheme, onReset, onToggleProfile }) {
  return (
    <header className="relative z-10">
      <div className="flex items-center gap-3 px-5 py-3">
        <h1 className="flex shrink-0 items-center gap-2 whitespace-nowrap text-sm font-semibold">
          <span className="accent-fill size-2 rounded-full" />
          <span className="text-neutral-100">Taste</span>
          <span className="accent-text">Agent</span>
        </h1>

        <div className="mx-auto">
          <ThemeSwitcher theme={theme} onChange={onTheme} />
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {health && (
            <>
              <span className="hidden sm:inline-flex">
                <Badge
                  label={health.mode === 'live' ? 'Qloo live' : 'Qloo mock'}
                  ok={health.mode === 'live'}
                />
              </span>
              <Badge label={health.brain} ok={health.brain !== 'rules'} />
            </>
          )}
          <button
            type="button"
            onClick={onToggleProfile}
            className="rounded-full border border-white/10 px-3 py-1 text-xs text-neutral-400 transition-colors hover:bg-white/5 hover:text-neutral-200 lg:hidden"
          >
            Profile
          </button>
          <button
            type="button"
            onClick={onReset}
            className="shrink-0 whitespace-nowrap rounded-full border border-white/10 px-3 py-1 text-xs text-neutral-300 transition-colors hover:bg-white/5"
          >
            New session
          </button>
        </div>
      </div>
      <div className="accent-rule h-px w-full opacity-70" />
    </header>
  )
}

function Badge({ label, ok }) {
  return (
    <span className="flex items-center gap-1.5 rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-neutral-300">
      <span className={`size-1.5 rounded-full ${ok ? 'bg-emerald-400' : 'bg-amber-400'}`} />
      {label}
    </span>
  )
}
