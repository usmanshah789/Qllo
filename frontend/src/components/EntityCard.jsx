import { pillarOf } from '../lib/pillars'

export default function EntityCard({ entity, onDislike }) {
  const pillar = pillarOf(entity.pillar)
  const affinity = entity.affinity != null ? Math.round(entity.affinity * 100) : null

  return (
    <article className="panel group relative flex gap-3 rounded-xl p-3 transition-colors hover:border-white/15">
      <Thumb entity={entity} />

      <div className="min-w-0 flex-1">
        <div className="flex items-baseline gap-2">
          <Title entity={entity} />
          {/* Qloo puts a year here for films but the whole address for places,
              which would crowd out the name. Only show the short kind. */}
          {entity.subtitle && entity.subtitle.length <= 18 && (
            <span className="shrink-0 text-xs text-neutral-500">{entity.subtitle}</span>
          )}
          {onDislike && (
            <button
              type="button"
              onClick={() => onDislike(entity.id)}
              title="Not for me — do not show this again"
              className="ml-auto shrink-0 rounded px-1 text-neutral-600 opacity-0 transition hover:text-neutral-300 group-hover:opacity-100"
            >
              ×
            </button>
          )}
        </div>

        <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-neutral-500">
          {pillar && <span className={`size-1.5 rounded-full ${pillar.dot}`} />}
          <span>{entity.type_label}</span>
          {entity.rating != null && (
            <>
              <span className="text-neutral-700">·</span>
              <span className="tabular-nums text-neutral-400">
                {entity.rating}/{entity.rating_scale} {entity.rating_source}
              </span>
            </>
          )}
        </div>

        {affinity != null && <Affinity value={affinity} />}

        {entity.address && (
          <p className="mt-1.5 truncate text-xs text-neutral-500">{entity.address}</p>
        )}

        {entity.tags?.length > 0 && (
          <ul className="mt-2 flex flex-wrap gap-1">
            {entity.tags.slice(0, 3).map((tag) => (
              <li
                key={tag.id || tag.name}
                className="rounded-md border border-white/8 bg-white/5 px-1.5 py-0.5 text-[11px] text-neutral-400"
              >
                {tag.name}
              </li>
            ))}
          </ul>
        )}
      </div>
    </article>
  )
}

function Title({ entity }) {
  const classes = 'truncate text-sm font-medium text-neutral-100'
  if (!entity.link) return <h4 className={classes}>{entity.name}</h4>

  return (
    <h4 className="min-w-0 truncate">
      <a
        href={entity.link}
        target="_blank"
        rel="noreferrer noopener"
        title={entity.link}
        className={`${classes} underline decoration-white/20 underline-offset-2 hover:decoration-white/60`}
      >
        {entity.name}
      </a>
    </h4>
  )
}

// Qloo's affinity is the whole point of a recommendation, so show it as a
// measure rather than burying it in a number.
function Affinity({ value }) {
  return (
    <div className="mt-2 flex items-center gap-2">
      <div className="h-1 flex-1 overflow-hidden rounded-full bg-white/8">
        <div className="accent-fill h-full rounded-full" style={{ width: `${value}%` }} />
      </div>
      <span className="shrink-0 tabular-nums text-[11px] text-neutral-500">{value}%</span>
    </div>
  )
}

function Thumb({ entity }) {
  if (!entity.image) {
    return (
      <div className="grid size-14 shrink-0 place-items-center rounded-lg border border-white/8 bg-white/5 text-sm text-neutral-600">
        {entity.name.slice(0, 1)}
      </div>
    )
  }
  return (
    <img
      src={entity.image}
      alt=""
      loading="lazy"
      className="size-14 shrink-0 rounded-lg object-cover"
      onError={(e) => {
        e.currentTarget.style.display = 'none'
      }}
    />
  )
}
