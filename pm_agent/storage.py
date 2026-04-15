from __future__ import annotations

from .database import DatabaseStore
from .models import AgentState


class LocalStateStore:
    def __init__(self, database_url: str | None = None) -> None:
        self.database = DatabaseStore(database_url=database_url)

    def load_state(self) -> AgentState:
        payload = self.database.load_json("agent_states", "state_key", "global")
        if not payload:
            return AgentState()
        return AgentState.from_dict(payload)

    def save_state(self, state: AgentState) -> None:
        self.database.save_json("agent_states", "state_key", "global", state.to_dict())
