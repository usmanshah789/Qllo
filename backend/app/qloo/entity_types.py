"""Qloo entity types, grouped into the four pillars from the hackathon guide."""

ENTITY_TYPES = {
    "urn:entity:movie": "Movie",
    "urn:entity:tv_show": "TV Show",
    "urn:entity:book": "Book",
    "urn:entity:brand": "Brand",
    "urn:entity:artist": "Artist",
    "urn:entity:person": "Person",
    "urn:entity:actor": "Actor",
    "urn:entity:director": "Director",
    "urn:entity:author": "Author",
    "urn:entity:locality": "Locality",
    "urn:entity:videogame": "Video Game",
    "urn:entity:podcast": "Podcast",
    "urn:entity:place": "Place",
}

PILLARS = {
    "entertainment": {
        "label": "Entertainment & Media",
        "types": [
            "urn:entity:movie",
            "urn:entity:tv_show",
            "urn:entity:artist",
            "urn:entity:podcast",
            "urn:entity:book",
            "urn:entity:videogame",
        ],
    },
    "lifestyle": {
        "label": "Lifestyle, Dining & Travel",
        "types": [
            "urn:entity:place",
            "urn:entity:locality",
        ],
    },
    "retail": {
        "label": "Fashion, Retail & Brands",
        "types": [
            "urn:entity:brand",
        ],
    },
    "culture": {
        "label": "People, Culture & Creators",
        "types": [
            "urn:entity:person",
            "urn:entity:actor",
            "urn:entity:director",
            "urn:entity:author",
        ],
    },
}

#: Qloo lists 13 entity types, but the hackathon API does not accept all of
#: them everywhere. Probed against the live API:
#:   director  - rejected by both /search and /v2/insights
#:   actor     - /search returns nothing (actors come back as person)
#:   author    - searchable, but not a valid recommendation target
#:   locality  - searchable, but not a valid recommendation target
#: actor is also dropped as a target: it returns results but never an image,
#: and person covers the same people with pictures.
SEARCHABLE = tuple(t for t in ENTITY_TYPES if t not in ("urn:entity:director", "urn:entity:actor"))
RECOMMENDABLE = tuple(
    t for t in ENTITY_TYPES
    if t not in (
        "urn:entity:director",
        "urn:entity:author",
        "urn:entity:locality",
        "urn:entity:actor",
    )
)

#: What to search instead when a type cannot be searched directly.
SEARCH_SUBSTITUTE = {
    "urn:entity:director": "urn:entity:person",
    "urn:entity:actor": "urn:entity:person",
}

_TYPE_TO_PILLAR = {t: key for key, p in PILLARS.items() for t in p["types"]}

# Short aliases so callers (and the agent) can say "movie" instead of the full URN.
_ALIASES = {urn.rsplit(":", 1)[-1]: urn for urn in ENTITY_TYPES}


def normalize_type(value: str | None) -> str | None:
    """Accept 'movie' or 'urn:entity:movie' and always return the full URN."""
    if not value:
        return None
    value = value.strip()
    if value in ENTITY_TYPES:
        return value
    return _ALIASES.get(value.lower())


def searchable_type(value: str | None) -> str | None:
    """Swap a type Qloo will not search for the nearest one it will."""
    urn = normalize_type(value)
    if urn is None:
        return None
    return SEARCH_SUBSTITUTE.get(urn, urn)


def pillar_of(entity_type: str | None) -> str | None:
    return _TYPE_TO_PILLAR.get(normalize_type(entity_type) or "")


def types_for_pillar(pillar: str) -> list[str]:
    return list(PILLARS.get(pillar, {}).get("types", []))
