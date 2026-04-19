from __future__ import annotations

import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any

from openai import OpenAI

from .config import MODEL_CONFIG, MODEL_TIERS

logger = logging.getLogger(__name__)


@dataclass
class LlmFallbackStats:
    """记录降级过程的统计信息。"""
    attempts: list[dict[str, str]] = field(default_factory=list)
    final_tier: str = ""
    warning: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "attempts": self.attempts,
            "final_tier": self.final_tier,
            "warning": self.warning,
        }


class LlmClient:
    """多模型 LLM 客户端，支持 Tier-1 → Tier-2 → Tier-3 自动降级。"""

    def __init__(self, *, model_config: dict[str, dict] | None = None, tiers: list[str] | None = None) -> None:
        self._model_config = model_config or MODEL_CONFIG
        self._tiers = tiers or MODEL_TIERS
        self._clients: dict[str, OpenAI] = {}
        self._build_clients()

    def _build_clients(self) -> None:
        for tier_name in self._tiers:
            cfg = self._model_config.get(tier_name)
            if not cfg:
                continue
            # 支持 api_key 直接值或 api_key_env 环境变量名
            api_key = cfg.get("api_key") or os.getenv(cfg.get("api_key_env", ""), "")
            if not api_key:
                env_hint = cfg.get("api_key_env", "")
                if env_hint:
                    logger.warning("[llm] Tier '%s' 缺少 API key (直接值 api_key 或环境变量 %s)", tier_name, env_hint)
                else:
                    logger.warning("[llm] Tier '%s' 缺少 API key", tier_name)
                continue
            self._clients[tier_name] = OpenAI(
                api_key=api_key,
                base_url=cfg["base_url"],
                timeout=cfg.get("timeout", 30),
            )

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> tuple[str, LlmFallbackStats]:
        """发送聊天请求，自动从主模型降级到备用模型。

        返回 (response_text, stats)。
        """
        stats = LlmFallbackStats()
        last_error: Exception | None = None

        for tier_name in self._tiers:
            client = self._clients.get(tier_name)
            if not client:
                stats.attempts.append({"tier": tier_name, "status": "skipped", "reason": "no client"})
                continue

            cfg = self._model_config[tier_name]
            temp = temperature if temperature is not None else cfg.get("temperature", 0.3)
            tokens = max_tokens if max_tokens is not None else cfg.get("max_tokens", 4096)

            for attempt in range(2):
                try:
                    response = client.chat.completions.create(
                        model=cfg["model"],
                        messages=messages,
                        temperature=temp,
                        max_tokens=tokens,
                        stream=False,
                    )
                    text = response.choices[0].message.content or ""
                    stats.final_tier = tier_name
                    stats.attempts.append({"tier": tier_name, "status": "success", "attempt": attempt + 1})
                    return text, stats
                except Exception as exc:
                    last_error = exc
                    stats.attempts.append({"tier": tier_name, "status": "error", "attempt": attempt + 1, "error": str(exc)[:100]})
                    logger.warning("[llm] Tier '%s' 第%d次尝试失败: %s", tier_name, attempt + 1, exc)

        stats.warning = f"所有模型均失败，最后错误: {last_error}"
        raise last_error  # type: ignore[misc]

    def parse_json_response(self, text: str) -> dict[str, Any]:
        """从 LLM 返回文本中提取并解析 JSON。"""
        stripped = text.strip()
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", stripped)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法从 LLM 响应中解析 JSON: {text[:200]}")


def validate_llm_output(payload: dict[str, Any], mode: str) -> list[str]:
    """校验 LLM 返回的 JSON 是否合法。返回错误列表，空表示通过。"""
    errors: list[str] = []
    if "mode" not in payload or payload["mode"] != mode:
        errors.append(f"mode 字段缺失或不是 '{mode}'")

    if mode == "requirement_analysis":
        reqs = payload.get("requirements")
        if not reqs or not isinstance(reqs, list):
            errors.append("requirements 字段缺失或为空")
        else:
            for i, req in enumerate(reqs):
                if not req.get("title"):
                    errors.append(f"requirements[{i}].title 缺失")
                if req.get("priority") not in ("高", "中", "低", ""):
                    errors.append(f"requirements[{i}].priority 值非法: {req.get('priority')}")
                if req.get("complexity") not in ("低", "中", "高", ""):
                    errors.append(f"requirements[{i}].complexity 值非法")
                if req.get("risk") not in ("低", "中", "高", ""):
                    errors.append(f"requirements[{i}].risk 值非法")
    return errors
