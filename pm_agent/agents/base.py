from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ..llm_client import LlmClient
from ..pipeline import PipelineContext


class BaseAgent(ABC):
    """All sub-agents inherit from this base class."""

    mode: str = ""  # Subclass must set

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        self._llm = llm_client

    @abstractmethod
    def build_system_prompt(self, ctx: PipelineContext) -> str:
        """Build the system prompt."""

    @abstractmethod
    def build_user_prompt(self, ctx: PipelineContext) -> str:
        """Build the user prompt."""

    @abstractmethod
    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        """Parse LLM response, return structured result."""

    def execute(self, ctx: PipelineContext) -> dict[str, Any]:
        """Execute agent logic, call LLM and return result."""
        if not self._llm:
            return {
                "status": "skipped",
                "reply": "LLM 未配置，跳过",
                "data": {},
            }

        system = self.build_system_prompt(ctx)
        user = self.build_user_prompt(ctx)

        text, stats = self._llm.chat_completion([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])

        try:
            parsed = self._llm.parse_json_response(text)
        except ValueError as exc:
            return {
                "status": "failed",
                "reply": text[:200],
                "data": {},
                "error": str(exc),
                "llm_stats": stats.to_dict(),
            }

        result = self.parse_response(text, ctx)
        result["llm_stats"] = stats.to_dict()
        return result
