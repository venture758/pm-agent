from __future__ import annotations

import json
import re
from typing import Any

from openai import OpenAI

from .config import (
    NVIDIA_NIM_BASE_URL,
    NVIDIA_NIM_DEFAULT_MODEL,
    NVIDIA_NIM_DEFAULT_TEMPERATURE,
    NVIDIA_NIM_DEFAULT_MAX_TOKENS,
)


class LlmClient:
    """封装 NVIDIA NIM（OpenAI 兼容接口）的 LLM 客户端。"""

    def __init__(self, api_key: str, *, base_url: str = NVIDIA_NIM_BASE_URL) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat_completion(
        self,
        messages: list[dict[str, str]],
        *,
        model: str = NVIDIA_NIM_DEFAULT_MODEL,
        temperature: float = NVIDIA_NIM_DEFAULT_TEMPERATURE,
        max_tokens: int = NVIDIA_NIM_DEFAULT_MAX_TOKENS,
    ) -> str:
        """发送聊天消息并返回响应文本，支持自动重试。"""
        last_error: Exception | None = None
        for attempt in range(2):
            try:
                response = self._client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=False,
                )
                return response.choices[0].message.content or ""
            except Exception as exc:
                last_error = exc
        raise last_error  # type: ignore[misc]

    def parse_json_response(self, text: str) -> dict[str, Any]:
        """从 LLM 返回文本中提取并解析 JSON，容忍 markdown code block 包裹。"""
        stripped = text.strip()
        # 尝试直接解析
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            pass
        # 尝试提取 markdown code block
        match = re.search(r"```(?:json)?\s*\n([\s\S]*?)\n```", stripped)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        # 尝试从文本中找到第一个 { 到最后一个 }
        start = stripped.find("{")
        end = stripped.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(stripped[start : end + 1])
            except json.JSONDecodeError:
                pass
        raise ValueError(f"无法从 LLM 响应中解析 JSON: {text[:200]}")
