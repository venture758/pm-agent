from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from .models import (
    AssignmentRecommendation,
    ChatSession,
    ConfirmedAssignment,
    ImportBatch,
    KnowledgeUpdateRecord,
    MemberProfile,
    ModuleKnowledgeEntry,
    RequirementItem,
    StoryRecord,
    SyncAction,
    TaskRecord,
)
from .utils import normalize_requirement_id


@dataclass
class WorkspaceUpload:
    kind: str
    original_name: str
    file_size: int = 0
    storage_backend: str = "database"
    uploaded_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> "WorkspaceUpload":
        return cls(
            kind=str(payload.get("kind") or ""),
            original_name=str(payload.get("original_name") or ""),
            file_size=int(payload.get("file_size") or 0),
            storage_backend=str(payload.get("storage_backend") or "database"),
            uploaded_at=str(payload.get("uploaded_at") or datetime.utcnow().isoformat()),
        )


@dataclass
class WorkspaceState:
    workspace_id: str
    title: str = ""
    draft_mode: str = "chat"
    message_text: str = ""
    current_session_id: str = ""
    current_session_requirement_ids: list[str] = field(default_factory=list)
    requirement_rows: list[dict[str, Any]] = field(default_factory=list)
    team_rows: list[dict[str, Any]] = field(default_factory=list)
    managed_members: list[MemberProfile] = field(default_factory=list)
    module_entries: list[ModuleKnowledgeEntry] = field(default_factory=list)
    normalized_requirements: list[RequirementItem] = field(default_factory=list)
    member_profiles: list[MemberProfile] = field(default_factory=list)
    recommendations: list[AssignmentRecommendation] = field(default_factory=list)
    confirmed_assignments: list[ConfirmedAssignment] = field(default_factory=list)
    handoff_stories: list[StoryRecord] = field(default_factory=list)
    handoff_tasks: list[TaskRecord] = field(default_factory=list)
    latest_sync_batch: Optional[ImportBatch] = None
    latest_story_import: Optional[dict[str, Any]] = None
    latest_task_import: Optional[dict[str, Any]] = None
    uploads: list[WorkspaceUpload] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)
    chat_messages: list[dict[str, Any]] = field(default_factory=list)
    chat_sessions: list[ChatSession] = field(default_factory=list)
    active_session_id: str = ""
    latest_knowledge_update: Optional[KnowledgeUpdateRecord] = None
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "WorkspaceState":
        batch = payload.get("latest_sync_batch")
        session_ids: list[str] = []
        for item in payload.get("current_session_requirement_ids", []):
            normalized = normalize_requirement_id(item)
            if normalized and normalized not in session_ids:
                session_ids.append(normalized)
        return cls(
            workspace_id=payload["workspace_id"],
            title=payload.get("title", ""),
            draft_mode=payload.get("draft_mode", "chat"),
            message_text=payload.get("message_text", ""),
            current_session_id=str(payload.get("current_session_id") or ""),
            current_session_requirement_ids=session_ids,
            requirement_rows=list(payload.get("requirement_rows", [])),
            team_rows=list(payload.get("team_rows", [])),
            managed_members=[MemberProfile(**item) for item in payload.get("managed_members", [])],
            module_entries=[
                ModuleKnowledgeEntry.from_payload(item)
                for item in payload.get("module_entries", [])
            ],
            normalized_requirements=[
                RequirementItem(**item) for item in payload.get("normalized_requirements", [])
            ],
            member_profiles=[MemberProfile(**item) for item in payload.get("member_profiles", [])],
            recommendations=[
                AssignmentRecommendation(**item) for item in payload.get("recommendations", [])
            ],
            confirmed_assignments=[
                ConfirmedAssignment(**item) for item in payload.get("confirmed_assignments", [])
            ],
            handoff_stories=[StoryRecord(**item) for item in payload.get("handoff_stories", [])],
            handoff_tasks=[TaskRecord(**item) for item in payload.get("handoff_tasks", [])],
            latest_sync_batch=(
                ImportBatch(
                    **{
                        **batch,
                        "actions": [SyncAction(**action) for action in batch.get("actions", [])],
                    }
                )
                if batch
                else None
            ),
            latest_story_import=payload.get("latest_story_import"),
            latest_task_import=payload.get("latest_task_import"),
            uploads=[WorkspaceUpload.from_payload(item) for item in payload.get("uploads", [])],
            messages=list(payload.get("messages", [])),
            chat_messages=list(payload.get("chat_messages", [])),
            chat_sessions=[ChatSession(**item) for item in payload.get("chat_sessions", [])],
            active_session_id=str(payload.get("active_session_id") or ""),
            latest_knowledge_update=(
                KnowledgeUpdateRecord.from_payload(payload.get("latest_knowledge_update"))
                if payload.get("latest_knowledge_update")
                else None
            ),
            updated_at=payload.get("updated_at", datetime.utcnow().isoformat()),
        )
