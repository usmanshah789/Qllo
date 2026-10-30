import { THEMES } from '../lib/themes'

export default function ThemeSwitcher({ theme, onChange }) {
  return (
    <div className="hidden items-center gap-0.5 rounded-full border border-white/10 bg-white/5 p-0.5 md:flex">
      {THEMES.map((option) => {
        const active = option.key === theme
        return (
          <button
            key={option.key}
            type="button"
            onClick={() => onChange(option.key)}
            className={`flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs transition-colors ${
              active ? 'bg-white/10 text-neutral-100' : 'text-neutral-500 hover:text-neutral-300'
            }`}
          >
            <span
              className="size-1.5 rounded-full"
              style={{ backgroundColor: option.swatch }}
            />
            {option.label}
          </button>
        )
      })}
    </div>
  )
}
