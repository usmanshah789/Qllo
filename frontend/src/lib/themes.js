// Five palettes. Each one only moves the two accent hues and the glow behind
// the page; the greys stay put so text contrast never changes with the theme.
export const THEMES = [
  { key: 'aurora', label: 'Aurora', swatch: '#a78bfa' },
  { key: 'candy', label: 'Candy', swatch: '#f472b6' },
  { key: 'sunset', label: 'Sunset', swatch: '#fb923c' },
  { key: 'jade', label: 'Jade', swatch: '#34d399' },
  { key: 'royal', label: 'Royal', swatch: '#fbbf24' },
]

export const DEFAULT_THEME = 'aurora'
const STORAGE_KEY = 'taste-agent:theme'

export function loadTheme() {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    if (THEMES.some((t) => t.key === saved)) return saved
  } catch {
    // Private windows and blocked storage both land here; the default is fine.
  }
  return DEFAULT_THEME
}

export function saveTheme(key) {
  document.documentElement.dataset.theme = key
  try {
    localStorage.setItem(STORAGE_KEY, key)
  } catch {
    // Not worth failing a click over.
  }
}
