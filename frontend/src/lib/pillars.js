// Mirrors the four pillars the backend groups Qloo's entity types into.
export const PILLARS = [
  {
    key: 'entertainment',
    label: 'Entertainment',
    dot: 'bg-amber-400',
    ask: 'What should I watch or listen to next?',
  },
  {
    key: 'lifestyle',
    label: 'Lifestyle & Travel',
    dot: 'bg-emerald-400',
    ask: 'Where should I eat or spend an evening?',
  },
  {
    key: 'retail',
    label: 'Fashion & Brands',
    dot: 'bg-sky-400',
    ask: 'What brand would suit me?',
  },
  {
    key: 'culture',
    label: 'People & Culture',
    dot: 'bg-violet-400',
    ask: 'Whose work should I be following?',
  },
]

export const pillarOf = (key) => PILLARS.find((p) => p.key === key)
