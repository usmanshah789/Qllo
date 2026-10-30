"""Offline stand-in for the Qloo API.

Same method signatures and same normalized return types as QlooClient, so the
rest of the app cannot tell the difference. Results are deterministic: the same
signals always produce the same ranking, which keeps demos repeatable.
"""

import hashlib

from app.qloo.entity_types import ENTITY_TYPES, normalize_type, types_for_pillar
from app.qloo.models import Entity, Tag, entity_from_raw, tag_from_raw


def _tag_urn(label: str) -> str:
    return "urn:tag:keyword:qloo:" + label.lower().replace(" ", "_").replace("-", "_")


def _mk(entity_id: str, name: str, entity_type: str, description: str, tags: list[str]) -> dict:
    return {
        "entity_id": entity_id,
        "name": name,
        "type": entity_type,
        "properties": {"description": description},
        "tags": [{"tag_id": _tag_urn(t), "name": t.title(), "type": "urn:tag:keyword:qloo"} for t in tags],
    }


CATALOG: list[dict] = [
    # --- Entertainment & Media ---
    _mk("mock:movie:inception", "Inception", "urn:entity:movie",
        "A thief who steals corporate secrets through dream-sharing technology.",
        ["sci-fi", "cerebral", "heist", "dreamlike"]),
    _mk("mock:movie:blade-runner-2049", "Blade Runner 2049", "urn:entity:movie",
        "A young blade runner uncovers a secret that could tip society into chaos.",
        ["cyberpunk", "neo-noir", "atmospheric", "sci-fi"]),
    _mk("mock:movie:her", "Her", "urn:entity:movie",
        "A lonely writer falls in love with an operating system.",
        ["melancholy", "near-future", "romance", "minimalist"]),
    _mk("mock:movie:parasite", "Parasite", "urn:entity:movie",
        "A poor family schemes their way into a wealthy household.",
        ["social satire", "thriller", "korean", "dark comedy"]),
    _mk("mock:tv:severance", "Severance", "urn:entity:tv_show",
        "Office workers surgically divide their work and personal memories.",
        ["corporate surreal", "mystery", "minimalist", "slow burn"]),
    _mk("mock:tv:mr-robot", "Mr. Robot", "urn:entity:tv_show",
        "A cybersecurity engineer is recruited by an anarchist hacker group.",
        ["hacker", "paranoid", "cyberpunk", "techno-thriller"]),
    _mk("mock:artist:bonobo", "Bonobo", "urn:entity:artist",
        "Downtempo producer blending organic instruments with electronic texture.",
        ["downtempo", "electronic", "chill", "atmospheric"]),
    _mk("mock:artist:ryuichi-sakamoto", "Ryuichi Sakamoto", "urn:entity:artist",
        "Composer known for spare piano works and ambient film scores.",
        ["ambient", "minimalist", "japanese", "film score"]),
    _mk("mock:podcast:darknet-diaries", "Darknet Diaries", "urn:entity:podcast",
        "True stories from the dark side of the internet.",
        ["true crime", "hacking", "investigative"]),
    _mk("mock:book:neuromancer", "Neuromancer", "urn:entity:book",
        "The novel that defined cyberpunk fiction.",
        ["cyberpunk", "sci-fi", "noir"]),
    _mk("mock:videogame:death-stranding", "Death Stranding", "urn:entity:videogame",
        "A courier reconnects a fractured America across haunted terrain.",
        ["atmospheric", "surreal", "open world", "melancholy"]),

    # --- Lifestyle, Dining & Travel ---
    _mk("mock:place:blue-bottle-aoyama", "Blue Bottle Coffee Aoyama", "urn:entity:place",
        "Pared-back specialty coffee bar with concrete and timber interiors.",
        ["specialty coffee", "minimalist", "tokyo", "third wave"]),
    _mk("mock:place:bar-benfiddich", "Bar Benfiddich", "urn:entity:place",
        "Apothecary-style cocktail bar where herbs are ground to order.",
        ["cocktails", "craft", "tokyo", "intimate"]),
    _mk("mock:place:fuglen-tokyo", "Fuglen Tokyo", "urn:entity:place",
        "Norwegian coffee house and cocktail bar with mid-century furniture.",
        ["coffee", "scandinavian", "design-led", "tokyo"]),
    _mk("mock:place:trunk-shibuya", "Trunk Hotel Shibuya", "urn:entity:place",
        "Boutique hotel built around a socially-minded design philosophy.",
        ["boutique hotel", "design", "tokyo"]),
    _mk("mock:locality:shimokitazawa", "Shimokitazawa, Tokyo", "urn:entity:locality",
        "Low-rise Tokyo neighbourhood of vintage shops and tiny live houses.",
        ["vintage", "indie", "walkable", "tokyo"]),
    _mk("mock:locality:kreuzberg", "Kreuzberg, Berlin", "urn:entity:locality",
        "Berlin district known for nightlife, street art and record stores.",
        ["nightlife", "street art", "berlin", "alternative"]),

    # --- Fashion, Retail & Brands ---
    _mk("mock:brand:muji", "MUJI", "urn:entity:brand",
        "Japanese retailer built on no-logo, utilitarian product design.",
        ["minimalist", "japanese", "functional", "no-brand"]),
    _mk("mock:brand:acne-studios", "Acne Studios", "urn:entity:brand",
        "Stockholm fashion house with a stark, architectural silhouette.",
        ["scandinavian", "fashion", "minimalist"]),
    _mk("mock:brand:teenage-engineering", "Teenage Engineering", "urn:entity:brand",
        "Swedish maker of playful, precisely designed synthesizers.",
        ["industrial design", "music tech", "playful", "swedish"]),
    _mk("mock:brand:a24", "A24", "urn:entity:brand",
        "Studio and label with a distinctive arthouse identity.",
        ["arthouse", "film", "design-led"]),

    # --- People, Culture & Creators ---
    _mk("mock:director:denis-villeneuve", "Denis Villeneuve", "urn:entity:director",
        "Director of atmospheric, large-scale science fiction.",
        ["sci-fi", "atmospheric", "auteur"]),
    _mk("mock:director:wong-kar-wai", "Wong Kar-wai", "urn:entity:director",
        "Filmmaker known for saturated colour and romantic longing.",
        ["romantic", "stylized", "hong kong"]),
    _mk("mock:actor:tilda-swinton", "Tilda Swinton", "urn:entity:actor",
        "Actor drawn to formally adventurous, arthouse projects.",
        ["arthouse", "avant-garde"]),
    _mk("mock:author:haruki-murakami", "Haruki Murakami", "urn:entity:author",
        "Novelist of quiet surrealism and jazz-soaked loneliness.",
        ["surreal", "japanese", "melancholy", "literary"]),
    _mk("mock:person:kengo-kuma", "Kengo Kuma", "urn:entity:person",
        "Architect working in timber, light and restraint.",
        ["architecture", "japanese", "natural materials", "minimalist"]),
]

TAG_CATALOG = [
    {"id": "urn:tag:genre:media:cyberpunk", "name": "Cyberpunk", "type": "genre"},
    {"id": "urn:tag:genre:media:sci_fi", "name": "Science Fiction", "type": "genre"},
    {"id": "urn:tag:keyword:minimalist", "name": "Minimalist", "type": "keyword"},
    {"id": "urn:tag:keyword:atmospheric", "name": "Atmospheric", "type": "keyword"},
    {"id": "urn:tag:keyword:melancholy", "name": "Melancholy", "type": "keyword"},
    {"id": "urn:tag:keyword:japanese", "name": "Japanese", "type": "keyword"},
    {"id": "urn:tag:keyword:design_led", "name": "Design-led", "type": "keyword"},
    {"id": "urn:tag:keyword:specialty_coffee", "name": "Specialty Coffee", "type": "keyword"},
    {"id": "urn:tag:genre:media:thriller", "name": "Thriller", "type": "genre"},
    {"id": "urn:tag:keyword:vintage", "name": "Vintage", "type": "keyword"},
]


def _score(seed: str, entity_id: str) -> float:
    """Stable pseudo-affinity in the 0.55-0.98 range."""
    digest = hashlib.sha256(f"{seed}|{entity_id}".encode()).hexdigest()
    return round(0.55 + (int(digest[:6], 16) % 430) / 1000, 3)


def _to_entity(raw: dict, affinity: float | None = None) -> Entity:
    entity = entity_from_raw(raw)
    entity.affinity = affinity
    return entity


class MockQlooClient:
    mode = "mock"

    async def search(self, query: str, entity_type: str | None = None, take: int = 10) -> list[Entity]:
        wanted = normalize_type(entity_type)
        needle = query.lower().strip()

        hits = [
            raw for raw in CATALOG
            if (not wanted or raw["type"] == wanted)
            and (needle in raw["name"].lower() or any(needle in t["name"].lower() for t in raw["tags"]))
        ]

        if not hits:
            # Any query should resolve to something, so the demo never dead-ends.
            fallback_type = wanted or "urn:entity:movie"
            slug = needle.replace(" ", "-") or "unknown"
            hits = [
                _mk(
                    f"mock:{fallback_type.rsplit(':', 1)[-1]}:{slug}",
                    query.strip().title() or "Unknown",
                    fallback_type,
                    f"Mock entity generated for this query.",
                    ["mock"],
                )
            ]

        return [_to_entity(raw, _score(needle, raw["entity_id"])) for raw in hits[:take]]

    async def insights(
        self,
        target_type: str,
        signal_entities: list[str] | None = None,
        signal_tags: list[str] | None = None,
        take: int = 10,
        location: str | None = None,
        filter_tags: list[str] | None = None,
    ) -> list[Entity]:
        # location/filter_tags are accepted so the signature matches the live
        # client; the fixed catalogue has nothing to narrow.
        wanted = normalize_type(target_type) or target_type
        seed = "|".join(sorted(signal_entities or []) + sorted(signal_tags or [])) or "default"

        pool = [raw for raw in CATALOG if raw["type"] == wanted]
        if not pool:
            pool = [raw for raw in CATALOG if raw["type"] in types_for_pillar("entertainment")]

        signal_ids = set(signal_entities or [])
        ranked = [
            _to_entity(raw, _score(seed, raw["entity_id"]))
            for raw in pool
            if raw["entity_id"] not in signal_ids
        ]
        ranked.sort(key=lambda e: e.affinity or 0, reverse=True)
        return ranked[:take]

    async def entities(self, entity_ids: list[str]) -> list[Entity]:
        index = {raw["entity_id"]: raw for raw in CATALOG}
        return [_to_entity(index[i]) for i in entity_ids if i in index]

    async def tags(self, query: str, take: int = 10) -> list[Tag]:
        needle = query.lower().strip()
        hits = [t for t in TAG_CATALOG if needle in t["name"].lower() or needle in t["id"]]
        return [tag_from_raw(t) for t in (hits or TAG_CATALOG)[:take]]

    async def compare(
        self,
        group_a: list[str],
        group_b: list[str],
        target_type: str,
        take: int = 10,
    ) -> list[Tag]:
        """Mirrors the live endpoint, which returns scored tags rather than entities."""
        seed = f"compare|{'|'.join(group_a)}|{'|'.join(group_b)}"
        scored = [
            tag_from_raw({**t, "query": {"score": _score(seed, t["id"])}})
            for t in TAG_CATALOG
        ]
        scored.sort(key=lambda t: t.score or 0, reverse=True)
        return scored[:take]


MOCK_TYPES = sorted({raw["type"] for raw in CATALOG})
assert all(t in ENTITY_TYPES for t in MOCK_TYPES)
