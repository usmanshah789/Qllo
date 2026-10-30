// The tags Qloo attaches to everything they like, ranked by what recurs.
// Nothing here is written by a model - it is counted, not generated.
export default function TasteRead({ read }) {
  if (!read?.ready) {
    const needed = read?.needed ?? 2
    return (
      <p className="mt-3 text-sm text-neutral-600">
        {needed === 1
          ? 'One more thing you like and I can read the thread running through it.'
          : 'Name a couple of things you like and I can read what runs through them.'}
      </p>
    )
  }

  return (
    <>
      <ul className="mt-3 flex flex-wrap gap-1.5">
        {read.signature.map((tag) => (
          <li
            key={tag.name}
            title={`${tag.family} · on ${tag.shared_by} of your signals`}
            className={`rounded-full border px-2.5 py-1 text-xs ${
              tag.shared_by > 1
                ? 'border-white/25 bg-white/10 text-neutral-100'
                : 'border-white/10 bg-white/5 text-neutral-400'
            }`}
          >
            {tag.name}
          </li>
        ))}
      </ul>
      <p className="mt-2.5 text-xs text-neutral-600">
        Drawn from {read.entity_count} of your signals
        {read.spans?.length > 1 && ` across ${read.spans.length} pillars`}.
      </p>
    </>
  )
}
