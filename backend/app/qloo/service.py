"""Picks the live or mock Qloo client based on config.

Everything else in the app calls get_client() and never imports a transport
directly, so adding the API key to .env is all that switches the app to live.
"""

from functools import lru_cache

from app import config
from app.qloo.client import QlooClient, QlooError
from app.qloo.mock import MockQlooClient

__all__ = ["get_client", "QlooError", "current_mode"]


@lru_cache(maxsize=1)
def get_client() -> QlooClient | MockQlooClient:
    if config.USE_MOCK:
        return MockQlooClient()
    return QlooClient(base_url=config.QLOO_BASE_URL, api_key=config.QLOO_API_KEY)


def current_mode() -> str:
    return get_client().mode
