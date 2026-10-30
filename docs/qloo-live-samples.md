# Qloo hackathon API — verified behaviour

Base URL: `https://hackathon.api.qloo.com`
Auth header: `X-Api-Key: <key>`

Everything below was confirmed against the live API, not taken from docs.

## Endpoints

| Call | Path | Key params |
|---|---|---|
| search | `GET /search` | `query`, `types`, `take` |
| insights | `GET /v2/insights` | `filter.type`, `signal.interests.entities`, `signal.interests.tags`, `take` |
| entity lookup | `GET /entities` | `entity_ids` |
| tag search | `GET /v2/tags` | `filter.query`, `take` |
| compare | `GET /v2/analysis/compare` | `a.signal.interests.entities`, `b.signal.interests.entities`, `filter.type` |

## Response shapes (they differ per endpoint)

- `/search` → `{"results": [ ...entities ]}` — a plain list.
- `/v2/insights` → `{"results": {"entities": [ ... ]}}`
- `/v2/tags` → `{"results": {"tags": [ ... ]}}`
- `/entities` → a top-level list.
- `/v2/analysis/compare` → `{"results": {"tags": [ ... ]}}` — **tags, not entities.**
  It answers "what separates these two groups" with scored tags.

## Gotchas found while testing

1. **Entity type lives in different fields.** Search results have
   `types: ["urn:entity:movie"]`. Insights results have `type: "urn:entity"`
   (generic, useless) and the real one in `subtype: "urn:entity:place"`.
   Read `type`, then `types`, then `subtype`, and take the first that resolves.
2. **`take` is ignored by compare.** Asking for 6 returns the full tag set, so
   trim client-side.
3. **`popularity` can be missing** on lower-ranked search hits — never format it
   without a None check.
4. **`description` is a paragraph.** `properties.short_descriptions[]` holds a
   one-line summary per language; prefer the `en` entry for UI.
5. **Affinity** sits at `query.affinity` on insights results, not at top level.
6. **Tag ids** are `tag_id` on entities but `id` in `/v2/tags` results.
7. Duplicate entities do appear in insights results (e.g. "Strawberry Fields"
   twice) — dedupe before display.

## Sanity results

Signal = *Inception* (`18B098FD-3D84-4609-BFF3-ADF9A0B00E40`):

- → brands: Tesla 0.972, Apple 0.956, Lamborghini 0.930
- → artists: Radiohead 0.941, Thom Yorke 0.935, Sigur Rós 0.932
- → places: One World Trade Center 0.935, Brooklyn Bridge 0.930

Place results skew to New York because Qloo weights filming locations, so a
location filter will matter once the agent asks for real travel suggestions.

Compare *Inception* vs *Severance* → Thriller 0.731, Sci-Fi 0.731,
Complex 0.730, Curious 0.730, Thrill-seeking 0.730.
