"""Serving the built React app from the API.

Keeping both behind one origin means one URL to share, no CORS, and nothing to
configure between the two halves. In development this does nothing - Vite
serves the UI and proxies /api here.
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import config


def mount(app: FastAPI) -> bool:
    dist = config.FRONTEND_DIST
    index = dist / "index.html"
    if not index.is_file():
        return False

    assets = dist / "assets"
    if assets.is_dir():
        app.mount("/assets", StaticFiles(directory=assets), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        # An unknown /api route is a mistake, not a page; saying so beats
        # handing the caller a page of HTML to parse.
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail=f"No route /{path}")

        # Real files (favicon, icons.svg) win; everything else is a route the
        # React router handles, so it gets index.html.
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and candidate.is_relative_to(dist.resolve()):
            return FileResponse(candidate)

        return FileResponse(index)

    return True
