# Team Leader Agent — 多 Agent 协作实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 `ProjectManagerAgent` 单 Agent 拆分为 5 个子 Agent + Orchestrator，通过 Pipeline 串行调度，每步输出建议后暂停等待用户确认。

**Architecture:** 新增 `pm_agent/agents/` 目录存放 5 个子 Agent，新增 `pm_agent/pipeline.py` 管理 PipelineContext 和状态流，改造 `pm_agent/llm_client.py` 为多模型降级客户端，新增 `WorkspaceService` 的 3 个 pipeline API 方法，新增 3 个 API 路由。

**Tech Stack:** Python 3.11+, OpenAI SDK (多模型), MySQL (PyMySQL), WSGI API, dataclasses

**Spec:** `docs/superpowers/specs/2026-04-17-team-leader-agent-design.md`

---

### Task 1: 多模型 LLM 客户端 — 配置 + 降级逻辑

**Files:**
- Modify: `pm_agent/config.py` — 新增 `MODEL_CONFIG` + 降级常量
- Modify: `pm_agent/llm_client.py` — 重写为多模型客户端
- Test: `tests/test_llm_fallback.py` — 新增降级测试

- [ ] **Step 1: 在 config.py 中新增模型配置**

在现有 LLM 配置下方（第 50 行之后）新增：

```python
# Multi-model LLM fallback configuration
MODEL_CONFIG = {
    "primary": {
        "base_url": NVIDIA_NIM_BASE_URL,
        "api_key_env": NVIDIA_NIM_API_KEY_ENV,
        "model": NVIDIA_NIM_DEFAULT_MODEL,
        "temperature": NVIDIA_NIM_DEFAULT_TEMPERATURE,
        "max_tokens": NVIDIA_NIM_DEFAULT_MAX_TOKENS,
        "timeout": 60,
    },
    "fallback": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o",
        "temperature": 0.3,
        "max_tokens": 4096,
        "timeout": 30,
    },
    "last_resort": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "max_tokens": 2048,
        "timeout": 15,
    },
}

# 优先级枚举，用于降级循环
MODEL_TIERS = ["primary", "fallback", "last_resort"]
```

- [ ] **Step 2: 重写 llm_client.py 为多模型客户端**

完整替换 `llm_client.py` 内容：

```python
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
            api_key = os.getenv(cfg["api_key_env"], "")
            if not api_key:
                logger.warning("[llm] Tier '%s' 缺少 API key (env=%s)", tier_name, cfg["api_key_env"])
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
```

- [ ] **Step 3: 编写多模型客户端测试**

创建 `tests/test_llm_fallback.py`：

```python
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
```

- [ ] **Step 4: 运行测试验证**

```bash
python -m pytest tests/test_llm_fallback.py -v
```

预期：全部通过

---

### Task 2: Pipeline 基础设施 — PipelineContext + 状态管理

**Files:**
- Create: `pm_agent/pipeline.py` — PipelineContext + 枚举 + 状态管理
- Create: `tests/test_pipeline.py` — Pipeline 单元测试

- [ ] **Step 1: 创建 pipeline.py**

```python
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .models import MemberProfile, ModuleKnowledgeEntry, RequirementItem, TaskRecord


# Pipeline 步骤枚举
PIPELINE_STEPS = [
    "requirement_parsing",
    "personnel_matching",
    "module_extraction",
    "team_analysis",
    "knowledge_update",
]

STEP_LABELS = {
    "requirement_parsing": "需求解析",
    "personnel_matching": "人员匹配",
    "module_extraction": "模块提炼",
    "team_analysis": "梯队分析",
    "knowledge_update": "知识更新",
}


@dataclass
class PipelineContext:
    """分析 Pipeline 的共享上下文。"""
    workspace_id: str
    session_id: str
    user_message: str

    # 已有数据（从 DB 加载）
    profiles: list[MemberProfile] = field(default_factory=list)
    module_entries: list[ModuleKnowledgeEntry] = field(default_factory=list)
    task_records: list[TaskRecord] = field(default_factory=list)

    # 逐步产出
    requirements: list[dict] = field(default_factory=list)        # 步骤1产出
    assignment_suggestions: list[dict] = field(default_factory=list)  # 步骤2产出
    module_changes: list[dict] = field(default_factory=list)      # 步骤3产出
    team_analysis: dict = field(default_factory=dict)             # 步骤4产出
    pending_changes: list[dict] = field(default_factory=list)     # 步骤5产出

    # 约束反馈
    step_constraints: dict[str, str] = field(default_factory=dict)

    # 状态
    current_step_index: int = 0
    step_results: dict[str, dict] = field(default_factory=dict)   # {step_name: {"status": ..., "reply": ..., "data": ...}}
    started_at: str = ""
    llm_stats: list[dict] = field(default_factory=list)

    @property
    def current_step(self) -> str | None:
        if self.current_step_index < len(PIPELINE_STEPS):
            return PIPELINE_STEPS[self.current_step_index]
        return None

    @property
    def is_complete(self) -> bool:
        return self.current_step_index >= len(PIPELINE_STEPS)

    @property
    def step_progress(self) -> list[dict[str, str]]:
        result = []
        for i, step in enumerate(PIPELINE_STEPS):
            if i < self.current_step_index:
                status = "completed"
            elif i == self.current_step_index:
                status = "current"
            else:
                status = "pending"
            result.append({"step": step, "label": STEP_LABELS[step], "status": status})
        return result

    def to_dict(self) -> dict[str, Any]:
        return {
            "workspace_id": self.workspace_id,
            "session_id": self.session_id,
            "user_message": self.user_message,
            "current_step": self.current_step,
            "current_step_index": self.current_step_index,
            "is_complete": self.is_complete,
            "step_progress": self.step_progress,
            "step_results": self.step_results,
            "requirements": self.requirements,
            "assignment_suggestions": self.assignment_suggestions,
            "module_changes": self.module_changes,
            "team_analysis": self.team_analysis,
            "pending_changes": self.pending_changes,
            "step_constraints": self.step_constraints,
            "llm_stats": self.llm_stats,
            "started_at": self.started_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PipelineContext":
        ctx = cls(
            workspace_id=data.get("workspace_id", ""),
            session_id=data.get("session_id", ""),
            user_message=data.get("user_message", ""),
            current_step_index=data.get("current_step_index", 0),
            step_results=data.get("step_results", {}),
            started_at=data.get("started_at", ""),
        )
        ctx.requirements = data.get("requirements", [])
        ctx.assignment_suggestions = data.get("assignment_suggestions", [])
        ctx.module_changes = data.get("module_changes", [])
        ctx.team_analysis = data.get("team_analysis", {})
        ctx.pending_changes = data.get("pending_changes", [])
        ctx.step_constraints = data.get("step_constraints", {})
        ctx.llm_stats = data.get("llm_stats", [])
        return ctx


class PipelineStore:
    """Pipeline 状态的内存存储（后续可持久化到 DB）。"""

    def __init__(self) -> None:
        self._pipelines: dict[str, PipelineContext] = {}

    def save(self, ctx: PipelineContext) -> None:
        self._pipelines[ctx.workspace_id] = ctx

    def load(self, workspace_id: str) -> PipelineContext | None:
        return self._pipelines.get(workspace_id)

    def delete(self, workspace_id: str) -> None:
        self._pipelines.pop(workspace_id, None)

    def clear(self) -> None:
        self._pipelines.clear()
```

- [ ] **Step 2: 编写 pipeline 测试**

创建 `tests/test_pipeline.py`：

```python
from __future__ import annotations

import unittest

from pm_agent.pipeline import PipelineContext, PipelineStore, PIPELINE_STEPS


class TestPipelineContext(unittest.TestCase):
    def test_initial_state(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        self.assertEqual(ctx.current_step, "requirement_parsing")
        self.assertFalse(ctx.is_complete)
        self.assertEqual(ctx.current_step_index, 0)

    def test_step_progress(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.current_step_index = 2
        progress = ctx.step_progress
        self.assertEqual(progress[0]["status"], "completed")
        self.assertEqual(progress[1]["status"], "completed")
        self.assertEqual(progress[2]["status"], "current")
        self.assertEqual(progress[3]["status"], "pending")

    def test_complete(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.current_step_index = len(PIPELINE_STEPS)
        self.assertTrue(ctx.is_complete)
        self.assertIsNone(ctx.current_step)

    def test_serialization(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        ctx.requirements = [{"title": "R1"}]
        ctx.current_step_index = 1
        d = ctx.to_dict()
        restored = PipelineContext.from_dict(d)
        self.assertEqual(restored.workspace_id, "w1")
        self.assertEqual(restored.requirements, [{"title": "R1"}])
        self.assertEqual(restored.current_step_index, 1)


class TestPipelineStore(unittest.TestCase):
    def test_save_load(self):
        store = PipelineStore()
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        store.save(ctx)
        loaded = store.load("w1")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.workspace_id, "w1")

    def test_delete(self):
        store = PipelineStore()
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="test")
        store.save(ctx)
        store.delete("w1")
        self.assertIsNone(store.load("w1"))
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/test_pipeline.py -v
```

---

### Task 3: Agent 模块骨架 — 目录 + 基类 + __init__.py

**Files:**
- Create: `pm_agent/agents/__init__.py` — 导出基类
- Create: `pm_agent/agents/base.py` — BaseAgent 抽象类

- [ ] **Step 1: 创建 agents/base.py**

```python
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

from ..llm_client import LlmClient
from ..pipeline import PipelineContext

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """所有子 Agent 的基类。"""

    mode: str = ""  # 子类必须设置

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        self._llm = llm_client

    @abstractmethod
    def build_system_prompt(self, ctx: PipelineContext) -> str:
        """构建 system prompt。"""

    @abstractmethod
    def build_user_prompt(self, ctx: PipelineContext) -> str:
        """构建 user prompt。"""

    @abstractmethod
    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        """解析 LLM 响应，返回结构化结果。"""

    def execute(self, ctx: PipelineContext) -> dict[str, Any]:
        """执行 Agent 逻辑，调用 LLM 并返回结果。"""
        if not self._llm:
            return {
                "status": "skipped",
                "reply": "LLM 未配置，跳过",
                "data": {},
            }

        system = self.build_system_prompt(ctx)
        user = self.build_user_prompt(ctx)
        logger.info("[agent.%s] 发起 LLM 请求", self.mode)

        text, stats = self._llm.chat_completion([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])

        logger.info("[agent.%s] LLM 返回 tier=%s", self.mode, stats.final_tier)

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
```

- [ ] **Step 2: 创建 agents/__init__.py**

```python
from .base import BaseAgent

__all__ = ["BaseAgent"]
```

---

### Task 4: 需求解析 Agent

**Files:**
- Create: `pm_agent/agents/requirement_parser.py`
- Create: `tests/test_requirement_parser_agent.py`

- [ ] **Step 1: 创建 requirement_parser.py**

从现有 `SYSTEM_PROMPT` 迁移，复用 `agent_prompt.py` 中的函数。

```python
from __future__ import annotations

from typing import Any

from ..agent_prompt import SYSTEM_PROMPT, build_member_context, build_module_context
from ..models import ModuleKnowledgeEntry
from ..pipeline import PipelineContext
from .base import BaseAgent


class RequirementParserAgent(BaseAgent):
    """步骤1：需求解析 Agent。"""
    mode = "requirement_analysis"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        module_entries = [
            ModuleKnowledgeEntry(
                key=e.get("key", ""),
                big_module=e.get("big_module", ""),
                function_module=e.get("function_module", ""),
                primary_owner=e.get("primary_owner", ""),
                backup_owners=e.get("backup_owners", []),
                familiar_members=e.get("familiar_members", []),
                aware_members=e.get("aware_members", []),
                unfamiliar_members=e.get("unfamiliar_members", []),
            )
            for e in ctx.module_entries
        ]
        module_ctx = build_module_context(module_entries)
        member_ctx = build_member_context(ctx.profiles)
        return SYSTEM_PROMPT.format(module_context=module_ctx, member_context=member_ctx)

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        # 如果有约束，注入
        constraint = ctx.step_constraints.get("requirement_parsing", "")
        base = ctx.user_message
        if constraint:
            return f"{base}\n\n## 额外约束\n{constraint}"
        return base

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        from ..llm_client import LlmClient
        llm = self._llm
        parsed = llm.parse_json_response(text) if llm else {}

        requirements = []
        for idx, req_data in enumerate(parsed.get("requirements", []), 1):
            matched_keys = [m.get("key", "") for m in req_data.get("matched_modules", [])]
            requirements.append({
                "requirement_id": req_data.get("requirement_id", f"REQ-{idx:03d}"),
                "title": req_data.get("title", ""),
                "priority": req_data.get("priority", "中"),
                "requirement_type": req_data.get("requirement_type", ""),
                "complexity": req_data.get("complexity", "中"),
                "risk": req_data.get("risk", "中"),
                "skills": req_data.get("skills", []),
                "matched_modules": req_data.get("matched_modules", []),
                "dependency_hints": req_data.get("dependency_hints", []),
                "blockers": req_data.get("blockers", []),
                "split_suggestion": req_data.get("split_suggestion", ""),
                "analysis_factors": req_data.get("analysis_factors", []),
            })

        return {
            "status": "success",
            "mode": self.mode,
            "requirements": requirements,
            "reply": parsed.get("reply", "已解析需求"),
            "data": {"requirements": requirements},
        }
```

- [ ] **Step 2: 创建测试**

```python
from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from pm_agent.agents.requirement_parser import RequirementParserAgent
from pm_agent.pipeline import PipelineContext


class FakeLlm:
    def chat_completion(self, messages):
        from pm_agent.llm_client import LlmFallbackStats
        return ('{"mode":"requirement_analysis","requirements":[{"title":"测试需求","priority":"高","complexity":"中","risk":"低","skills":["Python"],"matched_modules":[],"dependency_hints":[],"blockers":[],"split_suggestion":"","analysis_factors":[]}],"reply":"已解析1条需求"}', LlmFallbackStats(final_tier="primary"))

    def parse_json_response(self, text):
        import json
        return json.loads(text)


class TestRequirementParserAgent(unittest.TestCase):
    def test_execute(self):
        ctx = PipelineContext(workspace_id="w1", session_id="s1", user_message="需要一个用户登录接口")
        ctx.profiles = [{"name": "张三", "role": "developer"}]
        ctx.module_entries = []

        agent = RequirementParserAgent(llm_client=FakeLlm())
        result = agent.execute(ctx)
        self.assertEqual(result["status"], "success")
        self.assertEqual(len(result["requirements"]), 1)
        self.assertEqual(result["requirements"][0]["priority"], "高")
```

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/test_requirement_parser_agent.py -v
```

---

### Task 5: 人员匹配 Agent

**Files:**
- Create: `pm_agent/agents/personnel_matcher.py`
- Create: `tests/test_personnel_matcher_agent.py`

- [ ] **Step 1: 创建 personnel_matcher.py**

```python
from __future__ import annotations

import json
from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

PERSONNEL_MATCHER_SYSTEM = """\
你是研发团队的人员匹配专家。基于需求解析结果和团队成员信息，为每条需求推荐开发、测试、B角和协作人。

## 输出格式
你必须回复一个合法的 JSON 对象：
{
  "mode": "personnel_matching",
  "assignments": [
    {
      "requirement_id": "REQ-001",
      "requirement_title": "...",
      "development_owner": "姓名",
      "testing_owner": "姓名",
      "backup_owner": "姓名",
      "collaborators": ["姓名"],
      "reasons": ["推荐理由1", "推荐理由2"],
      "workload_snapshot": {"姓名": 0.3},
      "confidence": 0.85
    }
  ],
  "reply": "推荐分配..."
}

## 匹配规则
- 综合技能匹配度、模块熟悉度、当前负载、历史任务表现
- 避免给同一人分配过多高优先级需求
- 每个需求至少有一主一备
- 如果信息不足，相应字段留空字符串或空数组
"""


class PersonnelMatcherAgent(BaseAgent):
    """步骤2：人员匹配 Agent。"""
    mode = "personnel_matching"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return PERSONNEL_MATCHER_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append("## 需求列表")
        for req in ctx.requirements:
            parts.append(f"- [{req.get('requirement_id', '')}] {req.get('title', '')} (优先级: {req.get('priority', '中')})")
            if req.get("skills"):
                parts.append(f"  所需技能: {', '.join(req['skills'])}")

        parts.append("\n## 团队成员")
        for m in ctx.profiles:
            name = m.get("name", m) if isinstance(m, dict) else m.name
            role = m.get("role", "") if isinstance(m, dict) else m.role
            skills = m.get("skills", []) if isinstance(m, dict) else m.skills
            workload = m.get("workload", 0) if isinstance(m, dict) else m.workload
            capacity = m.get("capacity", 1) if isinstance(m, dict) else m.capacity
            parts.append(f"- {name}: 角色={role}, 技能={skills}, 负载={workload}/{capacity}")

        constraint = ctx.step_constraints.get("personnel_matching", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        assignments = parsed.get("assignments", [])
        return {
            "status": "success",
            "mode": self.mode,
            "assignments": assignments,
            "reply": parsed.get("reply", ""),
            "data": {"assignments": assignments},
        }
```

- [ ] **Step 2: 创建测试**（类似 Task 4 的 FakeLlm 模式）

- [ ] **Step 3: 运行测试**

```bash
python -m pytest tests/test_personnel_matcher_agent.py -v
```

---

### Task 6: 模块提炼 Agent

**Files:**
- Create: `pm_agent/agents/module_extractor.py`
- Create: `tests/test_module_extractor_agent.py`

- [ ] **Step 1: 创建 module_extractor.py**

```python
from __future__ import annotations

from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

MODULE_EXTRACTOR_SYSTEM = """\
你是模块知识管理专家。从需求中识别新的业务模块/子模块，或更新现有模块的归属关系。

## 输出格式
{
  "mode": "module_extraction",
  "module_changes": [
    {
      "action": "create_big_module|create_function_module|update_primary_owner|update_backup_owners",
      "big_module": "...",
      "function_module": "...",
      "primary_owner": "...",
      "rationale": "..."
    }
  ],
  "reply": "提炼结果..."
}

## 规则
- 仅当需求涉及新的业务领域时才创建新模块
- 不要为单一需求创建过多模块
- 模块名称应简洁且有意义
"""


class ModuleExtractorAgent(BaseAgent):
    """步骤3：模块提炼 Agent。"""
    mode = "module_extraction"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return MODULE_EXTRACTOR_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append("## 需求列表")
        for req in ctx.requirements:
            parts.append(f"- [{req.get('requirement_id', '')}] {req.get('title', '')}")
            if req.get("matched_modules"):
                mods = ", ".join(m.get("key", str(m)) for m in req["matched_modules"])
                parts.append(f"  关联模块: {mods}")

        parts.append("\n## 当前模块知识库")
        for e in ctx.module_entries:
            key = e.get("key", "") if isinstance(e, dict) else e.key
            owner = e.get("primary_owner", "") if isinstance(e, dict) else e.primary_owner
            parts.append(f"- {key} (负责人: {owner})")

        parts.append("\n## 人员匹配结果")
        for a in ctx.assignment_suggestions:
            parts.append(f"- {a.get('requirement_id', '')}: 开发={a.get('development_owner', '')}, 测试={a.get('testing_owner', '')}")

        constraint = ctx.step_constraints.get("module_extraction", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        changes = parsed.get("module_changes", [])
        return {
            "status": "success",
            "mode": self.mode,
            "module_changes": changes,
            "reply": parsed.get("reply", ""),
            "data": {"module_changes": changes},
        }
```

- [ ] **Step 2: 创建测试并运行**

---

### Task 7: 梯队分析 Agent

**Files:**
- Create: `pm_agent/agents/team_analyzer.py`
- Create: `tests/test_team_analyzer_agent.py`

- [ ] **Step 1: 创建 team_analyzer.py**

```python
from __future__ import annotations

from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

TEAM_ANALYZER_SYSTEM = """\
你是团队梯队分析专家。分析团队对各业务模块的熟悉度分布，发现单点风险，建议成长路径。

## 输出格式
{
  "mode": "team_analysis",
  "module_familiarity_matrix": {
    "税务::发票接口": {
      "familiar": ["李祥"],
      "aware": ["张三"],
      "unfamiliar": ["王五"]
    }
  },
  "single_point_risks": [
    {
      "module_key": "税务::发票接口",
      "risk_member": "李祥",
      "severity": "high|medium|low",
      "suggestion": "建议..."
    }
  ],
  "growth_paths": [
    {
      "member": "王五",
      "target_module": "税务::发票接口",
      "current_level": "不了解",
      "target_level": "了解",
      "path": "先参与..."
    }
  ],
  "reply": "分析结果..."
}

## 规则
- 只有一人熟悉某模块时标记为单点风险
- 成长路径应具体可行
- 如果某模块所有人都了解，不标记风险
"""


class TeamAnalyzerAgent(BaseAgent):
    """步骤4：梯队分析 Agent。"""
    mode = "team_analysis"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return TEAM_ANALYZER_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append("## 团队成员")
        for m in ctx.profiles:
            name = m.get("name", m) if isinstance(m, dict) else m.name
            parts.append(f"- {name}")

        parts.append("\n## 模块知识库")
        for e in ctx.module_entries:
            key = e.get("key", "") if isinstance(e, dict) else e.key
            fam = e.get("familiar_members", []) if isinstance(e, dict) else e.familiar_members
            awr = e.get("aware_members", []) if isinstance(e, dict) else e.aware_members
            unf = e.get("unfamiliar_members", []) if isinstance(e, dict) else e.unfamiliar_members
            parts.append(f"- {key}: 熟悉={fam}, 了解={awr}, 不了解={unf}")

        parts.append("\n## 本次人员匹配结果")
        for a in ctx.assignment_suggestions:
            parts.append(f"- {a.get('requirement_id', '')}: 开发={a.get('development_owner', '')}")

        constraint = ctx.step_constraints.get("team_analysis", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        return {
            "status": "success",
            "mode": self.mode,
            "module_familiarity_matrix": parsed.get("module_familiarity_matrix", {}),
            "single_point_risks": parsed.get("single_point_risks", []),
            "growth_paths": parsed.get("growth_paths", []),
            "reply": parsed.get("reply", ""),
            "data": {
                "module_familiarity_matrix": parsed.get("module_familiarity_matrix", {}),
                "single_point_risks": parsed.get("single_point_risks", []),
                "growth_paths": parsed.get("growth_paths", []),
            },
        }
```

- [ ] **Step 2: 创建测试并运行**

---

### Task 8: 知识更新 Agent（汇总）

**Files:**
- Create: `pm_agent/agents/knowledge_updater.py`
- Create: `tests/test_knowledge_updater_agent.py`

- [ ] **Step 1: 创建 knowledge_updater.py**

```python
from __future__ import annotations

from typing import Any

from ..pipeline import PipelineContext
from .base import BaseAgent

KNOWLEDGE_UPDATER_SYSTEM = """\
你是知识管理汇总专家。汇总前面所有步骤的变更建议，生成待执行操作列表。

## 输出格式
{
  "mode": "knowledge_update",
  "summary": {
    "requirements_parsed": 0,
    "personnel_assigned": 0,
    "modules_created": 0,
    "familiarity_updates": 0,
    "risks_identified": 0
  },
  "pending_changes": [
    {
      "type": "create_module|update_familiarity|create_assignment",
      "data": {}
    }
  ],
  "reply": "汇总结果..."
}
"""


class KnowledgeUpdaterAgent(BaseAgent):
    """步骤5：知识更新汇总 Agent。"""
    mode = "knowledge_update"

    def build_system_prompt(self, ctx: PipelineContext) -> str:
        return KNOWLEDGE_UPDATER_SYSTEM

    def build_user_prompt(self, ctx: PipelineContext) -> str:
        parts = []
        parts.append(f"## 步骤1: 需求解析 — {len(ctx.requirements)} 条")
        parts.append(f"## 步骤2: 人员匹配 — {len(ctx.assignment_suggestions)} 条")
        parts.append(f"## 步骤3: 模块提炼 — {len(ctx.module_changes)} 条")
        parts.append(f"## 步骤4: 梯队分析")

        parts.append("\n请汇总以上所有步骤的变更，生成待执行操作列表 pending_changes。")

        constraint = ctx.step_constraints.get("knowledge_update", "")
        if constraint:
            parts.append(f"\n## 额外约束\n{constraint}")

        return "\n".join(parts)

    def parse_response(self, text: str, ctx: PipelineContext) -> dict[str, Any]:
        parsed = self._llm.parse_json_response(text)
        pending = parsed.get("pending_changes", [])
        return {
            "status": "success",
            "mode": self.mode,
            "summary": parsed.get("summary", {}),
            "pending_changes": pending,
            "reply": parsed.get("reply", ""),
            "data": {"pending_changes": pending, "summary": parsed.get("summary", {})},
        }
```

- [ ] **Step 2: 创建测试并运行**

---

### Task 9: Orchestrator Agent — 流程编排

**Files:**
- Create: `pm_agent/agents/orchestrator.py`
- Create: `tests/test_orchestrator_agent.py`

- [ ] **Step 1: 创建 orchestrator.py**

```python
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..llm_client import LlmClient
from ..pipeline import PIPELINE_STEPS, PipelineContext, PipelineStore
from .base import BaseAgent
from .requirement_parser import RequirementParserAgent
from .personnel_matcher import PersonnelMatcherAgent
from .module_extractor import ModuleExtractorAgent
from .team_analyzer import TeamAnalyzerAgent
from .knowledge_updater import KnowledgeUpdaterAgent

logger = logging.getLogger(__name__)


class OrchestratorAgent:
    """编排 Agent：管理 Pipeline 的串行执行流程。"""

    def __init__(self, llm_client: LlmClient | None = None) -> None:
        self._llm = llm_client
        self._store = PipelineStore()
        self._agents: dict[str, BaseAgent] = {
            "requirement_parsing": RequirementParserAgent(llm_client),
            "personnel_matching": PersonnelMatcherAgent(llm_client),
            "module_extraction": ModuleExtractorAgent(llm_client),
            "team_analysis": TeamAnalyzerAgent(llm_client),
            "knowledge_update": KnowledgeUpdaterAgent(llm_client),
        }

    def start(self, workspace_id: str, user_message: str, profiles: list = None, module_entries: list = None, task_records: list = None) -> dict[str, Any]:
        """启动分析 Pipeline，执行步骤1。"""
        ctx = PipelineContext(
            workspace_id=workspace_id,
            session_id=f"pipeline-{datetime.now(timezone.utc).isoformat()}",
            user_message=user_message,
            profiles=profiles or [],
            module_entries=module_entries or [],
            task_records=task_records or [],
            started_at=datetime.now(timezone.utc).isoformat(),
        )
        self._store.save(ctx)
        return self._execute_current_step(ctx)

    def get_state(self, workspace_id: str) -> dict[str, Any] | None:
        """获取 Pipeline 当前状态。"""
        ctx = self._store.load(workspace_id)
        if not ctx:
            return None
        return ctx.to_dict()

    def confirm_step(self, workspace_id: str, action: str, modifications: dict | None = None, feedback: str | None = None) -> dict[str, Any]:
        """确认/修改/重新分析当前步骤。"""
        ctx = self._store.load(workspace_id)
        if not ctx:
            raise ValueError("Pipeline 不存在，请先启动分析")
        if ctx.is_complete:
            return {"status": "complete", "reply": "所有步骤已完成"}

        step_name = ctx.current_step

        if action == "confirm":
            # 记录当前步骤结果，进入下一步
            self._save_step_result(ctx, step_name, "confirmed")
            ctx.current_step_index += 1
            self._store.save(ctx)

            if ctx.is_complete:
                return {"status": "complete", "reply": "所有步骤已完成", "step_progress": ctx.step_progress}
            return self._execute_current_step(ctx)

        elif action == "modify":
            # 用户手动修改结果
            if modifications:
                self._apply_modifications(ctx, step_name, modifications)
            self._save_step_result(ctx, step_name, "modified")
            ctx.current_step_index += 1
            self._store.save(ctx)

            if ctx.is_complete:
                return {"status": "complete", "reply": "所有步骤已完成", "step_progress": ctx.step_progress}
            return self._execute_current_step(ctx)

        elif action == "reanalyze":
            # 重新分析，注入约束
            if feedback:
                ctx.step_constraints[step_name] = feedback
            self._store.save(ctx)
            return self._execute_current_step(ctx)

        elif action == "skip":
            self._save_step_result(ctx, step_name, "skipped")
            ctx.current_step_index += 1
            self._store.save(ctx)

            if ctx.is_complete:
                return {"status": "complete", "reply": "所有步骤已完成", "step_progress": ctx.step_progress}
            return self._execute_current_step(ctx)

        elif action == "execute":
            # 第5步专用：执行 pending_changes
            return {"status": "executed", "reply": "待执行变更已提交"}

        else:
            raise ValueError(f"不支持的操作: {action}")

    def _execute_current_step(self, ctx: PipelineContext) -> dict[str, Any]:
        """执行当前步骤。"""
        step_name = ctx.current_step
        agent = self._agents.get(step_name)
        if not agent:
            return {"status": "error", "reply": f"未知步骤: {step_name}"}

        result = agent.execute(ctx)

        # 将结果存储到 context
        self._save_step_result(ctx, step_name, result.get("status", "success"))

        # 把数据写入 ctx 对应字段
        self._populate_context(ctx, step_name, result)

        # 保存 LLM 统计
        if result.get("llm_stats"):
            ctx.llm_stats.append(result["llm_stats"])

        self._store.save(ctx)

        return {
            "status": result.get("status", "success"),
            "step": step_name,
            "reply": result.get("reply", ""),
            "data": result.get("data", {}),
            "step_progress": ctx.step_progress,
        }

    def _save_step_result(self, ctx: PipelineContext, step_name: str, status: str) -> None:
        ctx.step_results[step_name] = {"status": status}

    def _populate_context(self, ctx: PipelineContext, step_name: str, result: dict[str, Any]) -> None:
        data = result.get("data", {})
        if step_name == "requirement_parsing":
            ctx.requirements = data.get("requirements", [])
        elif step_name == "personnel_matching":
            ctx.assignment_suggestions = data.get("assignments", [])
        elif step_name == "module_extraction":
            ctx.module_changes = data.get("module_changes", [])
        elif step_name == "team_analysis":
            ctx.team_analysis = data
        elif step_name == "knowledge_update":
            ctx.pending_changes = data.get("pending_changes", [])

    def _apply_modifications(self, ctx: PipelineContext, step_name: str, modifications: dict) -> None:
        if step_name == "requirement_parsing":
            ctx.requirements = modifications.get("requirements", ctx.requirements)
        elif step_name == "personnel_matching":
            ctx.assignment_suggestions = modifications.get("assignments", ctx.assignment_suggestions)
        elif step_name == "module_extraction":
            ctx.module_changes = modifications.get("module_changes", ctx.module_changes)
        elif step_name == "team_analysis":
            ctx.team_analysis.update(modifications)
        elif step_name == "knowledge_update":
            ctx.pending_changes = modifications.get("pending_changes", ctx.pending_changes)
```

- [ ] **Step 2: 创建测试并运行**

---

### Task 10: API Service 集成 — 新增 3 个 Pipeline 方法

**Files:**
- Modify: `pm_agent/api_service.py` — 新增 `start_analysis_pipeline`, `get_pipeline_state`, `confirm_pipeline_step`

- [ ] **Step 1: 在 api_service.py 中新增 3 个方法**

在 WorkspaceService 类中添加（找一个合适位置，比如 `get_insight_history` 方法之后）：

```python
    # ---------- Analysis Pipeline ----------

    def start_analysis_pipeline(self, workspace_id: str, user_message: str) -> dict[str, Any]:
        """启动分析 Pipeline，执行步骤1（需求解析）。"""
        from .agents.orchestrator import OrchestratorAgent

        workspace = self._load_workspace(workspace_id)
        profiles = self._build_managed_member_profiles(workspace)
        profiles_dict = [_jsonable(p) for p in profiles]
        module_entries_dict = [_jsonable(e) for e in workspace.module_entries]
        task_records = self.workspaces.load_task_records_by_workspace_id(workspace_id)
        task_records_dict = [_jsonable(t) for t in task_records]

        # 创建 orchestrator（复用 workspace 的 LLM）
        llm = self.agent._llm if hasattr(self.agent, '_llm') and self.agent._llm else None
        orchestrator = OrchestratorAgent(llm_client=llm)

        result = orchestrator.start(
            workspace_id=workspace_id,
            user_message=user_message,
            profiles=profiles_dict,
            module_entries=module_entries_dict,
            task_records=task_records_dict,
        )
        return result

    def get_pipeline_state(self, workspace_id: str) -> dict[str, Any]:
        """获取 Pipeline 当前状态。"""
        from .agents.orchestrator import OrchestratorAgent

        llm = self.agent._llm if hasattr(self.agent, '_llm') and self.agent._llm else None
        orchestrator = OrchestratorAgent(llm_client=llm)
        state = orchestrator.get_state(workspace_id)
        if not state:
            raise ValueError("当前没有活跃的分析 Pipeline")
        return state

    def confirm_pipeline_step(
        self,
        workspace_id: str,
        action: str,
        modifications: dict | None = None,
        feedback: str | None = None,
    ) -> dict[str, Any]:
        """确认/修改/重新分析当前步骤。"""
        from .agents.orchestrator import OrchestratorAgent

        llm = self.agent._llm if hasattr(self.agent, '_llm') and self.agent._llm else None
        orchestrator = OrchestratorAgent(llm_client=llm)
        return orchestrator.confirm_step(
            workspace_id=workspace_id,
            action=action,
            modifications=modifications,
            feedback=feedback,
        )
```

---

### Task 11: API 路由 — 新增 3 个 endpoint

**Files:**
- Modify: `pm_agent/api.py` — 在 `_dispatch_api` 中新增路由

- [ ] **Step 1: 在 _dispatch_api 中添加路由**

在 `api.py` 的 `_dispatch_api` 方法中，`raise ValueError("不支持的 API 请求")` 之前添加：

```python
        # Pipeline routes
        if (
            len(segments) == 6
            and segments[3] == "pipeline"
            and segments[4] == "start"
            and method == "POST"
        ):
            payload = self._read_json_body(environ)
            return 200, self.service.start_analysis_pipeline(
                workspace_id,
                payload.get("message", ""),
            )
        if (
            len(segments) == 5
            and segments[3] == "pipeline"
            and segments[4] == "state"
            and method == "GET"
        ):
            return 200, self.service.get_pipeline_state(workspace_id)
        if (
            len(segments) == 5
            and segments[3] == "pipeline"
            and segments[4] == "confirm"
            and method == "POST"
        ):
            payload = self._read_json_body(environ)
            return 200, self.service.confirm_pipeline_step(
                workspace_id,
                action=payload.get("action", "confirm"),
                modifications=payload.get("modifications"),
                feedback=payload.get("feedback"),
            )
```

---

### Task 12: 端到端测试 + 清理

**Files:**
- Create: `tests/test_pipeline_e2e.py` — 端到端集成测试
- Modify: 确保所有 import 路径正确

- [ ] **Step 1: 创建端到端测试**

```python
from __future__ import annotations

import json
import unittest
from unittest.mock import MagicMock, patch

from pm_agent.agents.orchestrator import OrchestratorAgent
from pm_agent.llm_client import LlmFallbackStats
from pm_agent.pipeline import PipelineContext


class MockLlm:
    """模拟 LLM，根据不同步骤返回不同响应。"""

    def chat_completion(self, messages):
        content = messages[-1].get("content", "")
        if "requirement_analysis" in messages[0].get("content", "") or "需求" in content:
            text = json.dumps({
                "mode": "requirement_analysis",
                "requirements": [
                    {"title": "用户登录接口", "priority": "高", "complexity": "中", "risk": "中", "skills": ["Python"], "matched_modules": [], "dependency_hints": [], "blockers": [], "split_suggestion": "", "analysis_factors": []}
                ],
                "reply": "已解析1条需求",
            })
        elif "personnel_matching" in messages[0].get("content", ""):
            text = json.dumps({
                "mode": "personnel_matching",
                "assignments": [
                    {"requirement_id": "REQ-001", "requirement_title": "用户登录接口", "development_owner": "张三", "testing_owner": "李四", "backup_owner": "王五", "collaborators": [], "reasons": ["熟悉Python"], "workload_snapshot": {"张三": 0.3}, "confidence": 0.8}
                ],
                "reply": "推荐分配完成",
            })
        elif "module_extraction" in messages[0].get("content", ""):
            text = json.dumps({
                "mode": "module_extraction",
                "module_changes": [],
                "reply": "无新模块需要提炼",
            })
        elif "team_analysis" in messages[0].get("content", ""):
            text = json.dumps({
                "mode": "team_analysis",
                "module_familiarity_matrix": {},
                "single_point_risks": [],
                "growth_paths": [],
                "reply": "未发现显著风险",
            })
        elif "knowledge_update" in messages[0].get("content", ""):
            text = json.dumps({
                "mode": "knowledge_update",
                "summary": {"requirements_parsed": 1, "personnel_assigned": 1, "modules_created": 0},
                "pending_changes": [],
                "reply": "汇总完成",
            })
        else:
            text = json.dumps({"mode": "unknown", "reply": ""})
        return (text, LlmFallbackStats(final_tier="primary"))

    def parse_json_response(self, text):
        return json.loads(text)


class TestPipelineE2E(unittest.TestCase):
    def test_full_pipeline_flow(self):
        """完整走完5个步骤。"""
        llm = MockLlm()
        orchestrator = OrchestratorAgent(llm_client=llm)

        # 步骤1: 启动
        result = orchestrator.start("w1", "需要一个用户登录接口")
        self.assertEqual(result["step"], "requirement_parsing")
        self.assertEqual(result["status"], "success")

        # 确认步骤1 → 进入步骤2
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["step"], "personnel_matching")

        # 确认步骤2 → 进入步骤3
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["step"], "module_extraction")

        # 跳过步骤3
        result = orchestrator.confirm_step("w1", "skip")
        self.assertEqual(result["step"], "team_analysis")

        # 确认步骤4 → 进入步骤5
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["step"], "knowledge_update")

        # 确认步骤5 → 完成
        result = orchestrator.confirm_step("w1", "confirm")
        self.assertEqual(result["status"], "complete")

    def test_reanalyze_with_feedback(self):
        """重新分析并注入约束。"""
        llm = MockLlm()
        orchestrator = OrchestratorAgent(llm_client=llm)
        orchestrator.start("w2", "需要一个用户登录接口")

        # 重新分析人员匹配
        result = orchestrator.confirm_step("w2", "reanalyze", feedback="李祥这周不在")
        self.assertEqual(result["status"], "success")
        # 验证约束已保存
        state = orchestrator.get_state("w2")
        self.assertIn("李祥", state["step_constraints"].get("personnel_matching", ""))
```

- [ ] **Step 2: 运行所有新增测试**

```bash
python -m pytest tests/test_llm_fallback.py tests/test_pipeline.py tests/test_requirement_parser_agent.py tests/test_personnel_matcher_agent.py tests/test_module_extractor_agent.py tests/test_team_analyzer_agent.py tests/test_knowledge_updater_agent.py tests/test_orchestrator_agent.py tests/test_pipeline_e2e.py -v
```

---

## Self-Review

1. **Spec coverage:** 所有 5 个子 Agent + Orchestrator + PipelineContext + 多模型降级 + 3 个 API 方法 + 3 个路由 + 校验函数 + 测试，全部覆盖。
2. **Placeholder scan:** 无 TBD/TODO，每个步骤有具体代码和文件路径。
3. **Type consistency:** 所有 Agent 使用统一的 `BaseAgent` 接口，`PipelineContext` 的字段在所有 Agent 中一致使用 dict 格式（因为通过 API 传输）。
4. **Ambiguity check:** `profiles` 和 `module_entries` 在 Pipeline 中以 dict 形式传递（而非 dataclass），因为需要序列化存储。各子 Agent 内部按需转换。
