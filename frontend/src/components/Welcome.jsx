const EXAMPLES = [
  'I love Blade Runner 2049 and MUJI',
  'severance, radiohead, and good coffee',
  "I'm in Tokyo — where should I eat?",
]

export default function Welcome({ greeting, onPick }) {
  return (
    <div className="mx-auto max-w-lg py-14 text-center">
      <h2 className="text-xl font-medium">
        <span className="text-neutral-200">Your taste, </span>
        <span className="accent-text">followed somewhere new.</span>
      </h2>
      <p className="mt-3 text-sm leading-relaxed text-neutral-500">{greeting}</p>

      <ul className="mt-8 space-y-2">
        {EXAMPLES.map((example) => (
          <li key={example}>
            <button
              type="button"
              onClick={() => onPick(example)}
              className="panel w-full rounded-xl px-4 py-2.5 text-sm text-neutral-400 transition-colors hover:border-white/20 hover:text-neutral-200"
            >
              {example}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
