"""Live Qloo API client.

Endpoint shapes were taken from the official harness (`qloo api <cmd> --dry-run`):
    GET /search              query, types, take
    GET /v2/insights         filter.type, signal.interests.entities, signal.interests.tags, take
    GET /entities            entity_ids
    GET /v2/analysis/compare a.signal.interests.entities, b.signal.interests.entities, filter.type
    GET /v2/tags             filter.query

All five were verified against the live hackathon API.
"""

from typing import Any

import httpx

from app.qloo.entity_types import normalize_type, searchable_type
from app.qloo.models import Entity, Tag, entity_from_raw, tag_from_raw


class QlooError(RuntimeError):
    """Raised when Qloo rejects a request or is unreachable."""


def _extract_entities(payload: Any) -> list[dict]:
    """Qloo returns results either as a list or nested under results.entities."""
    if isinstance(payload, dict):
        results = payload.get("results", payload)
        if isinstance(results, dict):
            for key in ("entities", "entity", "items"):
                if isinstance(results.get(key), list):
                    return results[key]
            return []
        if isinstance(results, list):
            return results
    if isinstance(payload, list):
        return payload
    return []


def _extract_tags(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        results = payload.get("results", payload)
        if isinstance(results, dict) and isinstance(results.get("tags"), list):
            return results["tags"]
        if isinstance(results, list):
            return results
    if isinstance(payload, list):
        return payload
    return []


class QlooClient:
    mode = "live"

    def __init__(self, base_url: str, api_key: str, timeout: float = 20.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout

    async def _get(self, path: str, params: dict) -> Any:
        clean = {k: v for k, v in params.items() if v not in (None, "", [])}
        headers = {"X-Api-Key": self.api_key, "Accept": "application/json"}
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as http:
                res = await http.get(f"{self.base_url}{path}", params=clean, headers=headers)
        except httpx.HTTPError as exc:
            raise QlooError(f"Qloo request failed: {exc}") from exc

        if res.status_code == 401 or res.status_code == 403:
            raise QlooError("Qloo rejected the API key (401/403).")
        if res.status_code >= 400:
            raise QlooError(f"Qloo returned {res.status_code}: {res.text[:200]}")
        return res.json()

    async def search(self, query: str, entity_type: str | None = None, take: int = 10) -> list[Entity]:
        payload = await self._get(
            "/search",
            {"query": query, "types": searchable_type(entity_type), "take": take},
        )
        return [entity_from_raw(e) for e in _extract_entities(payload)]

    async def insights(
        self,
        target_type: str,
        signal_entities: list[str] | None = None,
        signal_tags: list[str] | None = None,
        take: int = 10,
        location: str | None = None,
        filter_tags: list[str] | None = None,
    ) -> list[Entity]:
        payload = await self._get(
            "/v2/insights",
            {
                "filter.type": normalize_type(target_type) or target_type,
                "signal.interests.entities": ",".join(signal_entities or []),
                "signal.interests.tags": ",".join(signal_tags or []),
                "filter.location.query": location,
                "filter.tags": ",".join(filter_tags or []),
                "take": take,
            },
        )
        return [entity_from_raw(e) for e in _extract_entities(payload)]

    async def entities(self, entity_ids: list[str]) -> list[Entity]:
        payload = await self._get("/entities", {"entity_ids": ",".join(entity_ids)})
        return [entity_from_raw(e) for e in _extract_entities(payload)]

    async def tags(self, query: str, take: int = 10) -> list[Tag]:
        payload = await self._get("/v2/tags", {"filter.query": query, "take": take})
        return [tag_from_raw(t) for t in _extract_tags(payload)]

    async def compare(
        self,
        group_a: list[str],
        group_b: list[str],
        target_type: str,
        take: int = 10,
    ) -> list[Tag]:
        """Qloo answers a comparison with the TAGS that separate the two groups."""
        payload = await self._get(
            "/v2/analysis/compare",
            {
                "a.signal.interests.entities": ",".join(group_a),
                "b.signal.interests.entities": ",".join(group_b),
                "filter.type": normalize_type(target_type) or target_type,
                "take": take,
            },
        )
        # compare ignores `take` server-side, so trim here.
        return [tag_from_raw(t) for t in _extract_tags(payload)][:take]
