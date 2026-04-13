from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Any, Iterable, Optional

from .config import COMPLEXITY_SCORES, FAMILIARITY_SCORES, PRIORITY_SCORES, RISK_SCORES


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\u3000", " ").strip()


def normalize_requirement_id(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return normalize_text(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return str(int(value))
        return normalize_text(value)
    text = normalize_text(value)
    if not text:
        return ""
    match = re.fullmatch(r"([+-]?\d+)\.0+", text)
    if match:
        return match.group(1)
    return text


def normalize_name(value: Any) -> str:
    return re.sub(r"[\s,，;；()（）]+", "", normalize_text(value))


def split_names(value: Any) -> list[str]:
    text = normalize_text(value)
    if not text:
        return []
    parts = re.split(r"[，,;；、/]+", text)
    return [normalize_text(part) for part in parts if normalize_text(part)]


def unique_list(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = normalize_text(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result


def parse_date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    text = normalize_text(value)
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def safe_float(value: Any, default: float = 0.0) -> float:
    text = normalize_text(value)
    if not text:
        return default
    try:
        return float(text)
    except ValueError:
        return default


def parse_priority(text: str) -> str:
    normalized = normalize_text(text)
    match = re.search(r"优先级[:：]?\s*(高|中|低)", normalized)
    if match:
        return match.group(1)
    if "优先级高" in normalized:
        return "高"
    if "优先级低" in normalized:
        return "低"
    return "中"


def extract_urls(text: str) -> list[str]:
    return re.findall(r"https?://[^\s]+", normalize_text(text))


def strip_urls(text: str) -> str:
    return re.sub(r"https?://[^\s]+", "", normalize_text(text)).strip()


def split_numbered_blocks(text: str) -> list[tuple[str, str]]:
    lines = [line.rstrip() for line in normalize_text(text).splitlines() if line.strip()]
    blocks: list[tuple[str, list[str]]] = []
    current_id = ""
    current_lines: list[str] = []
    for line in lines:
        match = re.match(r"^\s*(\d+)[\.\、]?\s*(.*)$", line)
        if match:
            if current_lines:
                blocks.append((current_id, current_lines))
            current_id = match.group(1)
            current_lines = [match.group(2).strip()]
        else:
            if not current_lines:
                current_id = str(len(blocks) + 1)
            current_lines.append(line.strip())
    if current_lines:
        blocks.append((current_id or str(len(blocks) + 1), current_lines))
    return [(block_id, "\n".join(lines_in_block).strip()) for block_id, lines_in_block in blocks]


def extract_terms(text: str) -> list[str]:
    normalized = normalize_text(text)
    segments = re.findall(r"[\u4e00-\u9fffA-Za-z0-9]+", normalized)
    terms: list[str] = []
    for segment in segments:
        parts = re.split(r"[和与及、\-_/]", segment)
        for part in parts:
            part = normalize_text(part)
            if len(part) >= 2:
                terms.append(part)
    return unique_list(terms)


def overlap_score(left: str, right: str) -> int:
    left_terms = set(extract_terms(left))
    right_terms = set(extract_terms(right))
    score = len(left_terms & right_terms)
    if normalize_text(left) and normalize_text(left) in normalize_text(right):
        score += 3
    if normalize_text(right) and normalize_text(right) in normalize_text(left):
        score += 3
    return score


def classify_requirement_type(text: str) -> str:
    normalized = normalize_text(text)
    mapping = [
        ("接口", "接口改造"),
        ("授权", "授权流程"),
        ("RPA", "RPA需求"),
        ("报表", "报表需求"),
        ("采集", "采集需求"),
        ("优化", "优化需求"),
        ("修复", "缺陷修复"),
    ]
    for keyword, result in mapping:
        if keyword in normalized:
            return result
    return "通用需求"


def infer_complexity(text: str) -> tuple[str, list[str]]:
    normalized = normalize_text(text)
    score = 1
    factors: list[str] = []
    if any(keyword in normalized for keyword in ("替换", "新数据源", "架构", "跨模块")):
        score += 2
        factors.append("涉及替换、新数据源或架构级变更")
    if any(keyword in normalized for keyword in ("接口", "授权", "采集", "报表")):
        score += 1
        factors.append("涉及核心业务链路")
    if any(keyword in normalized for keyword in ("优化", "修复")):
        factors.append("需求包含优化或修复动作")
    if any(keyword in normalized for keyword in ("和", "及", "&", "、")):
        score += 1
        factors.append("标题中存在多个子项，可能需要拆分")
    if score >= COMPLEXITY_SCORES["高"]:
        return "高", factors
    if score >= COMPLEXITY_SCORES["中高"]:
        return "中高", factors
    if score >= COMPLEXITY_SCORES["中"]:
        return "中", factors
    return "低", factors


def infer_risk(text: str, priority: str, complexity: str) -> tuple[str, list[str]]:
    normalized = normalize_text(text)
    score = PRIORITY_SCORES.get(priority, 2) + COMPLEXITY_SCORES.get(complexity, 2) - 1
    reasons: list[str] = []
    if priority == "高":
        reasons.append("需求优先级高")
    if complexity in {"中高", "高"}:
        reasons.append("需求复杂度较高")
    if any(keyword in normalized for keyword in ("替换", "新数据源", "授权", "核心")):
        score += 1
        reasons.append("涉及高风险关键词")
    if score >= RISK_SCORES["高"]:
        return "高", reasons
    if score >= RISK_SCORES["中"]:
        return "中", reasons
    return "低", reasons


def infer_split_suggestion(text: str, complexity: str, risk: str) -> Optional[str]:
    normalized = normalize_text(text)
    if complexity in {"中高", "高"} or risk == "高":
        return "建议按开发、测试、联调或模块边界拆分子任务。"
    if any(keyword in normalized for keyword in ("和", "及", "&", "、")):
        return "建议将标题中的多个子项拆成独立故事或任务。"
    return None


def promote_familiarity(current_label: str, confirmed: bool = False) -> str:
    levels = ["不了解", "了解", "熟悉"]
    current = normalize_text(current_label)
    if current == "一般":
        current = "了解"
    if current not in levels:
        current = "不了解"
    index = levels.index(current)
    if confirmed and index < len(levels) - 1:
        return levels[index + 1]
    if index < 2:
        return levels[index + 1]
    return current


def familiarity_score(label: str) -> int:
    normalized = normalize_text(label)
    if normalized == "一般":
        normalized = "了解"
    return FAMILIARITY_SCORES.get(normalized, 0)


def priority_score(label: str) -> int:
    return PRIORITY_SCORES.get(normalize_text(label), 2)


def complexity_score(label: str) -> int:
    return COMPLEXITY_SCORES.get(normalize_text(label), 2)


def risk_score(label: str) -> int:
    return RISK_SCORES.get(normalize_text(label), 2)
