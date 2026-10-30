"""FastAPI entrypoint for the Qloo taste agent."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import config
from app.routers import qloo as qloo_routes
from app.routers import chat as chat_routes
from app.routers import sessions as session_routes
from app import static_site

app = FastAPI(title="Qloo Taste Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(qloo_routes.router)
app.include_router(session_routes.router)
app.include_router(chat_routes.router)


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "mode": "mock" if config.USE_MOCK else "live",
        "qloo_base_url": config.QLOO_BASE_URL,
        "qloo_key_present": bool(config.QLOO_API_KEY),
        "brain": config.LLM_PROVIDER if config.USE_LLM else "rules",
        "llm_model": config.llm_model() if config.USE_LLM else None,
    }


# Must come last: the catch-all route would otherwise shadow the API.
SERVING_UI = static_site.mount(app)
