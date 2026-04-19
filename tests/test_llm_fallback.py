from __future__ import annotations

import json
import os
import unittest
from unittest.mock import MagicMock, patch

from pm_agent.llm_client import LlmClient, validate_llm_output


class FakeCompletion:
    def __init__(self, text: str):
        self.choices = [MagicMock(message=MagicMock(content=text))]


class TestLlmClientFallback(unittest.TestCase):
    @patch("pm_agent.llm_client.OpenAI")
    def test_primary_success(self, mock_openai):
        """主模型成功返回。"""
        client = mock_openai.return_value
        client.chat.completions.create.return_value = FakeCompletion('{"mode": "test"}')

        llm = LlmClient(model_config={
            "primary": {"base_url": "http://test", "api_key_env": "TEST_KEY", "model": "m1", "temperature": 0.3, "max_tokens": 100, "timeout": 5},
        }, tiers=["primary"])
        with patch.dict(os.environ, {"TEST_KEY": "key123"}):
            # Rebuild after env patch
            llm._build_clients()
            text, stats = llm.chat_completion([{"role": "user", "content": "hi"}])
        self.assertEqual(text, '{"mode": "test"}')
        self.assertEqual(stats.final_tier, "primary")

    @patch("pm_agent.llm_client.OpenAI")
    def test_fallback_on_error(self, mock_openai):
        """主模型失败，自动降级到 fallback。"""
        primary_client = MagicMock()
        primary_client.chat.completions.create.side_effect = Exception("timeout")
        fallback_client = MagicMock()
        fallback_client.chat.completions.create.return_value = FakeCompletion('{"ok": true}')

        instances = {"primary": primary_client, "fallback": fallback_client}
        def side_effect(*args, **kwargs):
            return instances.get(kwargs.get("base_url", ""))

        mock_openai.side_effect = side_effect
        # 更简单的做法：直接构建 client 并注入
        config = {
            "primary": {"base_url": "http://p", "api_key_env": "PK", "model": "m1", "temperature": 0.3, "max_tokens": 100, "timeout": 5},
            "fallback": {"base_url": "http://f", "api_key_env": "FK", "model": "m2", "temperature": 0.3, "max_tokens": 100, "timeout": 5},
        }
        with patch.dict(os.environ, {"PK": "pk", "FK": "fk"}):
            llm = LlmClient(model_config=config, tiers=["primary", "fallback"])
            llm._clients["primary"] = primary_client
            llm._clients["fallback"] = fallback_client
            text, stats = llm.chat_completion([{"role": "user", "content": "hi"}])
        self.assertEqual(stats.final_tier, "fallback")


class TestValidateLlmOutput(unittest.TestCase):
    def test_valid_requirement(self):
        payload = {
            "mode": "requirement_analysis",
            "requirements": [{"title": "test", "priority": "高", "complexity": "中", "risk": "低"}],
        }
        self.assertEqual(validate_llm_output(payload, "requirement_analysis"), [])

    def test_missing_mode(self):
        self.assertTrue(validate_llm_output({}, "requirement_analysis"))

    def test_invalid_priority(self):
        payload = {
            "mode": "requirement_analysis",
            "requirements": [{"title": "test", "priority": "超高"}],
        }
        errors = validate_llm_output(payload, "requirement_analysis")
        self.assertTrue(any("priority" in e for e in errors))
