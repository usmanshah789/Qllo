"""The taste signature: what actually runs through everything they like.

Built by pulling the full tag set for each liked entity from Qloo and keeping
the tags that recur. Nothing is written by a model here - a tag either appears
on their entities or it does not.
"""

from collections import Counter

from app.qloo import get_client
from app.qloo.models import Tag
from app.qloo.service import QlooError
from app.storage.models import Session

MIN_SIGNALS = 2
TAKE = 10

#: Tag families worth showing a person. The rest (markets, competitors) are
#: facts about a business, not a description of taste.
DESCRIPTIVE = (
    "style", "aesthetic_property", "emotional_tone", "theme", "mood",
    "genre", "subgenre", "audience", "character", "plot", "lifestyle",
    "core_value", "keyword",
)


def _family(tag: Tag) -> str | None:
    kind = tag.type or ""
    for name in DESCRIPTIVE:
        if name in kind:
            return name
    return None


async def build(session: Session) -> dict:
    liked = session.profile.liked_entity_ids()

    if len(liked) < MIN_SIGNALS:
        return {
            "ready": False,
            "needed": MIN_SIGNALS - len(liked),
            "signature": [],
            "entity_count": len(liked),
        }

    try:
        entities = await get_client().entities(liked)
    except QlooError as exc:
        return {"ready": False, "error": str(exc), "signature": [], "entity_count": len(liked)}

    counts: Counter[str] = Counter()
    seen: dict[str, Tag] = {}
    for entity in entities:
        # Count each tag once per entity, so one richly tagged film cannot
        # dominate the signature.
        for tag in {t.name: t for t in entity.tags}.values():
            if _family(tag) is None:
                continue
            counts[tag.name] += 1
            seen.setdefault(tag.name, tag)

    ranked = counts.most_common()
    shared = [(name, count) for name, count in ranked if count > 1]

    # What recurs across their tastes is the interesting part. Only fall back to
    # single-entity tags when almost nothing overlaps yet.
    chosen = shared if len(shared) >= 4 else ranked

    signature = [
        {"name": name, "family": _family(seen[name]), "shared_by": count}
        for name, count in chosen[:TAKE]
    ]

    return {
        "ready": bool(signature),
        "signature": signature,
        "entity_count": len(entities),
        "spans": sorted({e.pillar for e in entities if e.pillar}),
    }
