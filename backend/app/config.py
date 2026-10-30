"""App configuration, loaded from the .env file at the project root."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parents[2]
# override=True so a stale key left in the OS environment cannot shadow .env.
load_dotenv(ROOT_DIR / ".env", override=True)

QLOO_BASE_URL = os.getenv("QLOO_BASE_URL", "https://hackathon.api.qloo.com")
QLOO_API_KEY = os.getenv("QLOO_API_KEY", "")

# No Qloo key yet -> the app serves mock data so the UI stays usable.
MOCK_MODE = os.getenv("QLOO_MOCK_MODE", "auto").lower()
if MOCK_MODE == "auto":
    USE_MOCK = not bool(QLOO_API_KEY)
else:
    USE_MOCK = MOCK_MODE in ("1", "true", "yes", "on")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-opus-5")

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")

# Whichever key is present wins; with neither, the rule-based planner answers.
if ANTHROPIC_API_KEY:
    LLM_PROVIDER = "anthropic"
elif GROQ_API_KEY:
    LLM_PROVIDER = "groq"
else:
    LLM_PROVIDER = "none"

USE_LLM = LLM_PROVIDER != "none"


def llm_model() -> str:
    return ANTHROPIC_MODEL if LLM_PROVIDER == "anthropic" else GROQ_MODEL

DATA_DIR = Path(os.getenv("DATA_DIR", ROOT_DIR / "data"))
SESSIONS_DIR = DATA_DIR / "sessions"

# Comma-separated in production. Render's fromService gives a bare hostname,
# so add the scheme when one is missing.
def _as_origin(value: str) -> str:
    value = value.strip().rstrip("/")
    if value and not value.startswith(("http://", "https://")):
        return f"https://{value}"
    return value


_EXTRA_ORIGINS = [o for o in map(_as_origin, os.getenv("CORS_ORIGINS", "").split(",")) if o]

CORS_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    *_EXTRA_ORIGINS,
]
