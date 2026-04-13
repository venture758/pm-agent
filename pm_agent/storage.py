from __future__ import annotations

import json
from pathlib import Path

from .config import DEFAULT_STATE_FILE, DEFAULT_STATE_ROOT
from .database import DatabaseStore
from .models import AgentState


class LocalStateStore:
    def __init__(
        self,
        root: str | Path = DEFAULT_STATE_ROOT,
        filename: str = DEFAULT_STATE_FILE,
        database_url: str | None = None,
    ) -> None:
        self.root = Path(root)
        self.filename = filename
        self.root.mkdir(parents=True, exist_ok=True)
        self.database = DatabaseStore(root=self.root, database_url=database_url)
        self._migrate_legacy_file_if_needed()

    @property
    def path(self) -> Path:
        return self.root / self.filename

    def load_state(self) -> AgentState:
        payload = self.database.load_json("agent_states", "state_key", "global")
        if not payload:
            return AgentState()
        return AgentState.from_dict(payload)

    def save_state(self, state: AgentState) -> None:
        self.database.save_json("agent_states", "state_key", "global", state.to_dict())

    def _migrate_legacy_file_if_needed(self) -> None:
        if self.database.load_json("agent_states", "state_key", "global") is not None:
            return
        if not self.path.exists():
            return
        payload = AgentState.from_dict(json.loads(self.path.read_text(encoding="utf-8")))
        self.database.save_json("agent_states", "state_key", "global", payload.to_dict())
