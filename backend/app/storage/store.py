"""JSON-file persistence for sessions.

One file per session under data/sessions/. Writes go to a temp file and are
then renamed, so a crash mid-write can never leave a half-written session
behind. A lock guards against two requests saving the same session at once.
"""

import json
import os
import tempfile
import threading
from pathlib import Path

from app import config
from app.storage.models import Session, SessionSummary


class SessionNotFound(KeyError):
    pass


class SessionStore:
    def __init__(self, directory: Path | None = None):
        self.directory = directory or config.SESSIONS_DIR
        self.directory.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()

    def _path(self, session_id: str) -> Path:
        # Session ids are generated, never user input, but a traversal guard is cheap.
        if "/" in session_id or "\\" in session_id or session_id.startswith("."):
            raise SessionNotFound(session_id)
        return self.directory / f"{session_id}.json"

    def create(self, title: str = "New session") -> Session:
        session = Session(title=title)
        self.save(session)
        return session

    def get(self, session_id: str) -> Session:
        path = self._path(session_id)
        if not path.exists():
            raise SessionNotFound(session_id)
        return Session.model_validate_json(path.read_text(encoding="utf-8"))

    def exists(self, session_id: str) -> bool:
        return self._path(session_id).exists()

    def save(self, session: Session) -> Session:
        session.touch()
        payload = session.model_dump_json(indent=2)
        path = self._path(session.id)

        with self._lock:
            # Write beside the target so the rename stays on one filesystem.
            fd, tmp_name = tempfile.mkstemp(dir=self.directory, suffix=".tmp")
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                os.replace(tmp_name, path)
            except BaseException:
                Path(tmp_name).unlink(missing_ok=True)
                raise
        return session

    def delete(self, session_id: str) -> None:
        path = self._path(session_id)
        if not path.exists():
            raise SessionNotFound(session_id)
        path.unlink()

    def list(self) -> list[SessionSummary]:
        summaries = []
        for path in self.directory.glob("*.json"):
            try:
                session = Session.model_validate_json(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, ValueError):
                # A corrupt file should not take the whole list down.
                continue
            summaries.append(session.summary())
        summaries.sort(key=lambda s: s.updated_at, reverse=True)
        return summaries


store = SessionStore()
