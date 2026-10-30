"""Normalized shapes returned by the Qloo layer.

Mock and live responses are both converted into these models, so nothing
downstream has to know which transport produced the data. Field choices follow
the real hackathon API payloads (see docs/qloo-live-samples.md).
"""

from pydantic import BaseModel, Field

from app.qloo.entity_types import ENTITY_TYPES, normalize_type, pillar_of


class Tag(BaseModel):
    id: str
    name: str
    type: str | None = None
    # Only set by compare(), where Qloo scores how much a tag separates two groups.
    score: float | None = None
    popularity: float | None = None


class Entity(BaseModel):
    id: str
    name: str
    type: str | None = None
    type_label: str | None = None
    pillar: str | None = None
    subtitle: str | None = None
    description: str | None = None
    image: str | None = None
    address: str | None = None
    link: str | None = None
    rating: float | None = None
    rating_scale: int | None = None
    rating_source: str | None = None
    affinity: float | None = None
    popularity: float | None = None
    tags: list[Tag] = Field(default_factory=list)


def _first_entity_type(raw: dict) -> str | None:
    """Search results carry types[]; insights results carry a bare "urn:entity"
    in `type` and the real one in `subtype`, so try every field in turn."""
    for key in ("type", "types", "subtype"):
        value = raw.get(key)
        if isinstance(value, list):
            value = value[0] if value else None
        resolved = normalize_type(value) if isinstance(value, str) else None
        if resolved:
            return resolved
    return None


def _description(props: dict) -> str | None:
    """Prefer the one-line summary; the main description runs several sentences."""
    shorts = props.get("short_descriptions")
    if isinstance(shorts, list):
        english = next((s for s in shorts if s.get("language") == "en"), None)
        chosen = english or (shorts[0] if shorts else None)
        if isinstance(chosen, dict) and chosen.get("value"):
            return chosen["value"]
    return props.get("description")


# Qloo attaches a lot of Wikipedia bookkeeping ("2003 establishments in
# California"). Those are facts, not taste, so rank the descriptive tags first
# and drop the encyclopaedic ones entirely.
_TAG_PRIORITY = (
    "aesthetic_property",
    "emotional_tone",
    "style",
    "theme",
    "mood",
    "genre",
    "subgenre",
    "audience",
    "character",
    "plot",
    "lifestyle",
    "core_value",
    "interest_adjacency",
    "keyword",
)
_TAG_EXCLUDE = ("wikipedia_category", "wikidata", "key_market", "competitor_brand")

#: Qloo attaches dozens of descriptive tags. Keeping a deep slice is what lets
#: the taste read find what actually recurs across domains; callers that send
#: tags to a model take only the first few.
TAG_LIMIT = 40


def _tag_rank(tag: "Tag") -> int:
    kind = tag.type or ""
    for index, marker in enumerate(_TAG_PRIORITY):
        if marker in kind:
            return index
    return len(_TAG_PRIORITY)


def _useful_tags(tags: list["Tag"]) -> list["Tag"]:
    kept = [t for t in tags if not any(bad in (t.type or "") for bad in _TAG_EXCLUDE)]
    kept.sort(key=_tag_rank)
    return kept or tags


def tag_from_raw(raw: dict) -> Tag:
    # compare() reports type as the generic "urn:tag" and puts the real one in subtype.
    tag_type = raw.get("type")
    if not tag_type or tag_type == "urn:tag":
        tag_type = raw.get("subtype") or tag_type

    query = raw.get("query") or {}

    return Tag(
        id=raw.get("id") or raw.get("tag_id") or "",
        name=raw.get("name") or raw.get("id") or "Unknown",
        type=tag_type,
        score=query.get("score"),
        popularity=raw.get("popularity"),
    )


def _first(external: dict, key: str) -> dict | None:
    rows = external.get(key)
    if isinstance(rows, list) and rows and isinstance(rows[0], dict):
        return rows[0]
    return None


def _link(props: dict, external: dict) -> str | None:
    """Somewhere the person can actually go and look at the thing."""
    site = props.get("website")
    if isinstance(site, str) and site.startswith("http"):
        return site

    imdb = _first(external, "imdb")
    if imdb and imdb.get("id"):
        return f"https://www.imdb.com/title/{imdb['id']}/"

    letterboxd = _first(external, "letterboxd")
    if letterboxd and letterboxd.get("id"):
        return f"https://letterboxd.com/film/{letterboxd['id']}/"

    google = _first(external, "google_place")
    if google and google.get("place_id"):
        return f"https://www.google.com/maps/place/?q=place_id:{google['place_id']}"

    instagram = _first(external, "instagram")
    if instagram and instagram.get("id"):
        return f"https://www.instagram.com/{instagram['id']}/"

    return None


def _rating(external: dict) -> tuple[float | None, int | None, str | None]:
    """A real score from a source people recognise, not Qloo's own affinity."""
    imdb = _first(external, "imdb")
    if imdb and isinstance(imdb.get("user_rating"), (int, float)):
        return float(imdb["user_rating"]), 10, "IMDb"

    advisor = _first(external, "tripadvisor")
    if advisor and isinstance(advisor.get("rating"), (int, float)):
        return float(advisor["rating"]), 5, "Tripadvisor"

    return None, None, None


def entity_from_raw(raw: dict) -> Entity:
    """Build an Entity from a Qloo API payload, tolerating missing fields."""
    props = raw.get("properties") or {}
    image = props.get("image")
    if isinstance(image, dict):
        image = image.get("url")

    entity_type = _first_entity_type(raw)
    query = raw.get("query") or {}

    tags = _useful_tags([tag_from_raw(t) for t in (raw.get("tags") or []) if isinstance(t, dict)])

    external = raw.get("external") or {}
    rating, scale, source = _rating(external)

    subtitle = raw.get("disambiguation")
    if subtitle is not None:
        subtitle = str(subtitle)

    return Entity(
        id=raw.get("entity_id") or raw.get("id") or "",
        name=raw.get("name") or "Unknown",
        type=entity_type,
        type_label=ENTITY_TYPES.get(entity_type or ""),
        pillar=pillar_of(entity_type),
        subtitle=subtitle,
        description=_description(props),
        image=image,
        address=props.get("address"),
        link=_link(props, external),
        rating=rating,
        rating_scale=scale,
        rating_source=source,
        affinity=query.get("affinity"),
        popularity=raw.get("popularity"),
        tags=tags[:TAG_LIMIT],
    )
