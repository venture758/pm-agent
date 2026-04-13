from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
import re
from typing import Any, Iterable, Mapping, Optional


@dataclass
class RequirementItem:
    requirement_id: str
    title: str
    source_url: str = ""
    priority: str = "中"
    raw_text: str = ""
    source: str = "chat"
    source_message: str = ""
    requirement_type: str = ""
    complexity: str = "中"
    risk: str = "中"
    skills: list[str] = field(default_factory=list)
    dependency_hints: list[str] = field(default_factory=list)
    blockers: list[str] = field(default_factory=list)
    split_suggestion: Optional[str] = None
    analysis_factors: list[str] = field(default_factory=list)
    matched_module_keys: list[str] = field(default_factory=list)


@dataclass
class MemberProfile:
    name: str
    role: str = "developer"
    skills: list[str] = field(default_factory=list)
    experience_level: str = "中"
    workload: float = 0.0
    capacity: float = 1.0
    constraints: list[str] = field(default_factory=list)
    module_familiarity: dict[str, str] = field(default_factory=dict)


@dataclass
class AssignmentHistoryEntry:
    requirement_id: str
    title: str
    development_owner: str
    testing_owner: str = ""
    collaborators: list[str] = field(default_factory=list)
    assigned_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    suggested_familiarity_updates: dict[str, str] = field(default_factory=dict)


@dataclass
class ModuleKnowledgeEntry:
    key: str
    big_module: str
    function_module: str
    primary_owner: str
    backup_owners: list[str] = field(default_factory=list)
    familiar_members: list[str] = field(default_factory=list)
    aware_members: list[str] = field(default_factory=list)
    unfamiliar_members: list[str] = field(default_factory=list)
    source_sheet: str = ""
    source_year: int = 0
    imported_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    recent_assignees: list[str] = field(default_factory=list)
    suggested_familiarity: dict[str, str] = field(default_factory=dict)
    assignment_history: list[AssignmentHistoryEntry] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.backup_owners = self._normalize_name_list(self.backup_owners)
        self.familiar_members = self._normalize_name_list(self.familiar_members)
        self.aware_members = self._normalize_name_list(self.aware_members)
        self.unfamiliar_members = self._normalize_name_list(self.unfamiliar_members)
        self._normalize_familiarity_groups()

    @staticmethod
    def _normalize_name_list(values: Iterable[str] | str | None) -> list[str]:
        if values is None:
            return []
        if isinstance(values, str):
            raw_values = [item for item in re.split(r"[，,;；、/]+", values)]
        else:
            raw_values = list(values)
        normalized: list[str] = []
        for item in raw_values:
            name = str(item or "").strip()
            if name and name not in normalized:
                normalized.append(name)
        return normalized

    def _normalize_familiarity_groups(self) -> None:
        # Keep one group per member with precedence: 熟悉 > 了解 > 不了解.
        familiar = self._normalize_name_list(self.familiar_members)
        aware = [name for name in self._normalize_name_list(self.aware_members) if name not in familiar]
        unfamiliar = [
            name
            for name in self._normalize_name_list(self.unfamiliar_members)
            if name not in familiar and name not in aware
        ]
        self.familiar_members = familiar
        self.aware_members = aware
        self.unfamiliar_members = unfamiliar

    @property
    def backup_owner(self) -> str:
        return self.backup_owners[0] if self.backup_owners else ""

    @backup_owner.setter
    def backup_owner(self, value: str) -> None:
        self.backup_owners = self._normalize_name_list([value] if value else [])

    @property
    def familiarity_by_member(self) -> dict[str, str]:
        mapping: dict[str, str] = {}
        for name in self.unfamiliar_members:
            mapping[name] = "不了解"
        for name in self.aware_members:
            mapping[name] = "了解"
        for name in self.familiar_members:
            mapping[name] = "熟悉"
        return mapping

    @familiarity_by_member.setter
    def familiarity_by_member(self, values: Mapping[str, str]) -> None:
        familiar: list[str] = []
        aware: list[str] = []
        unfamiliar: list[str] = []
        for raw_name, raw_level in dict(values or {}).items():
            name = str(raw_name or "").strip()
            level = str(raw_level or "").strip()
            if not name or not level:
                continue
            if level == "一般":
                level = "了解"
            if level == "熟悉":
                familiar.append(name)
            elif level == "了解":
                aware.append(name)
            elif level == "不了解":
                unfamiliar.append(name)
        self.familiar_members = familiar
        self.aware_members = aware
        self.unfamiliar_members = unfamiliar
        self._normalize_familiarity_groups()

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "ModuleKnowledgeEntry":
        data = dict(payload or {})
        history = [
            item if isinstance(item, AssignmentHistoryEntry) else AssignmentHistoryEntry(**item)
            for item in data.get("assignment_history", [])
        ]
        entry = cls(
            key=str(data.get("key") or ""),
            big_module=str(data.get("big_module") or ""),
            function_module=str(data.get("function_module") or ""),
            primary_owner=str(data.get("primary_owner") or ""),
            backup_owners=cls._normalize_name_list(data.get("backup_owners")),
            familiar_members=cls._normalize_name_list(data.get("familiar_members")),
            aware_members=cls._normalize_name_list(data.get("aware_members")),
            unfamiliar_members=cls._normalize_name_list(data.get("unfamiliar_members")),
            source_sheet=str(data.get("source_sheet") or ""),
            source_year=int(data.get("source_year") or 0),
            imported_at=str(data.get("imported_at") or datetime.utcnow().isoformat()),
            recent_assignees=[str(item) for item in data.get("recent_assignees", []) if str(item).strip()],
            suggested_familiarity={
                str(key): ("了解" if str(value) == "一般" else str(value))
                for key, value in dict(data.get("suggested_familiarity") or {}).items()
                if str(key).strip() and str(value).strip()
            },
            assignment_history=history,
        )
        if not entry.backup_owners and data.get("backup_owner"):
            entry.backup_owner = str(data.get("backup_owner"))
        if not entry.familiarity_by_member and data.get("familiarity_by_member"):
            entry.familiarity_by_member = dict(data.get("familiarity_by_member") or {})
        return entry


@dataclass
class AssignmentRecommendation:
    requirement_id: str
    title: str
    module_key: str = ""
    module_name: str = ""
    development_owner: str = ""
    testing_owner: str = ""
    backup_owner: str = ""
    collaborators: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    split_suggestion: Optional[str] = None
    unassigned_reason: str = ""
    workload_snapshot: dict[str, float] = field(default_factory=dict)
    confidence: float = 0.0


@dataclass
class ConfirmedAssignment:
    requirement_id: str
    title: str
    module_key: str = ""
    development_owner: str = ""
    testing_owner: str = ""
    backup_owner: str = ""
    collaborators: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    split_suggestion: Optional[str] = None
    action_log: list[str] = field(default_factory=list)
    story_code: str = ""
    task_codes: list[str] = field(default_factory=list)
    unassigned_reason: str = ""


@dataclass
class StoryRecord:
    user_story_code: str
    name: str
    user_story_name: str = ""
    sequence_no: float | None = None
    user_story_tag: str = ""
    status: str = ""
    remark: str = ""
    plan_test_completion_time: str = ""
    related_task_count: float | None = None
    owner: str = ""
    owner_names: str = ""
    tester: str = ""
    tester_names: str = ""
    requirement_owner_names: str = ""
    developers: list[str] = field(default_factory=list)
    developer_names: str = ""
    priority: str = "中"
    absolute_priority: float | None = None
    plan_test_date: str = ""
    planned_person_days: float = 0.0
    planned_dev_person_days: float = 0.0
    actual_person_days: float = 0.0
    related_case_count: float | None = None
    plan_trunk_test_completion_time: str = ""
    modified_time: str = ""
    acceptance_criteria: str = ""
    detail_url: str = ""
    project_status: str = ""
    iteration_phase: str = ""
    iteration_goal: str = ""
    release_plan: str = ""
    release_window: str = ""
    scrum_team: str = ""
    product_group: str = ""
    project_name: str = ""
    ksm_or_bug_no: str = ""
    story_type: str = ""
    cloud_name: str = ""
    application_name: str = ""
    related_story: str = ""
    related_requirement: str = ""
    completed_time: str = ""
    plan_baseline_test_completion_time: str = ""
    has_upgrade_notice: str = ""
    change_type: str = ""
    product: str = ""
    version: str = ""
    created_time: str = ""
    created_by: str = ""
    related_requirement_id: str = ""
    defects: int = 0
    related_defect_count: float | None = None
    module_path: str = ""


@dataclass
class TaskHistoryProfile:
    member_name: str
    total_tasks: int = 0
    design_coding_tasks: int = 0
    module_path_counts: dict[str, int] = field(default_factory=dict)
    story_task_counts: dict[str, int] = field(default_factory=dict)
    avg_actual_vs_planned: float = 0.0
    total_defects: int = 0


@dataclass
class TaskRecord:
    task_code: str
    story_code: str
    story_name: str
    name: str
    task_type: str = ""
    owner: str = ""
    status: str = ""
    estimated_start: str = ""
    estimated_end: str = ""
    planned_person_days: float = 0.0
    actual_person_days: float = 0.0
    participants: list[str] = field(default_factory=list)
    product: str = ""
    version: str = ""
    module_path: str = ""
    related_requirement_id: str = ""
    defects: int = 0


@dataclass
class SyncAction:
    entity_type: str
    record_code: str
    action: str
    changed_fields: list[str] = field(default_factory=list)


@dataclass
class ImportBatch:
    batch_id: str
    imported_at: str
    source_files: list[str] = field(default_factory=list)
    actions: list[SyncAction] = field(default_factory=list)


@dataclass
class ExecutionAlert:
    severity: str
    reason: str
    suggestion: str
    requirement_id: str = ""
    story_code: str = ""
    task_code: str = ""
    context: list[str] = field(default_factory=list)


@dataclass
class HeatmapEntry:
    member: str
    load: float
    capacity: float
    utilization: float
    level: str
    sources: list[str] = field(default_factory=list)


@dataclass
class SinglePointRisk:
    member: str
    module_key: str
    reason: str
    related_requirements: list[str] = field(default_factory=list)


@dataclass
class GrowthSuggestion:
    member: str
    module_key: str
    suggestion: str
    rationale: str


@dataclass
class InsightSnapshot:
    workspace_id: str
    snapshot_at: str
    heatmap: list[dict[str, Any]] = field(default_factory=list)
    single_points: list[dict[str, Any]] = field(default_factory=list)
    growth_suggestions: list[dict[str, Any]] = field(default_factory=list)
    summary: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    module_entries: dict[str, ModuleKnowledgeEntry] = field(default_factory=dict)
    confirmed_assignments: dict[str, ConfirmedAssignment] = field(default_factory=dict)
    stories: dict[str, StoryRecord] = field(default_factory=dict)
    tasks: dict[str, TaskRecord] = field(default_factory=dict)
    import_batches: list[ImportBatch] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "AgentState":
        return cls(
            module_entries={
                key: ModuleKnowledgeEntry.from_payload({**value, "key": value.get("key") or key})
                for key, value in payload.get("module_entries", {}).items()
            },
            confirmed_assignments={
                key: ConfirmedAssignment(**value) for key, value in payload.get("confirmed_assignments", {}).items()
            },
            stories={key: StoryRecord(**value) for key, value in payload.get("stories", {}).items()},
            tasks={key: TaskRecord(**value) for key, value in payload.get("tasks", {}).items()},
            import_batches=[
                ImportBatch(
                    **{
                        **batch,
                        "actions": [SyncAction(**action) for action in batch.get("actions", [])],
                    }
                )
                for batch in payload.get("import_batches", [])
            ],
        )
