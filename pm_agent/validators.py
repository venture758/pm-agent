from __future__ import annotations

from .models import AssignmentRecommendation, ConfirmedAssignment, GrowthSuggestion, HeatmapEntry, ImportBatch


def validate_recommendations(recommendations: list[AssignmentRecommendation]) -> None:
    for recommendation in recommendations:
        if not recommendation.requirement_id:
            raise ValueError("分配建议缺少 requirement_id")
        if not recommendation.title:
            raise ValueError("分配建议缺少标题")
        if not recommendation.development_owner and not recommendation.unassigned_reason:
            raise ValueError(f"需求 {recommendation.requirement_id} 既无开发负责人，也无未分配原因")


def validate_confirmed_assignments(assignments: list[ConfirmedAssignment]) -> None:
    for assignment in assignments:
        if not assignment.requirement_id:
            raise ValueError("确认分配缺少 requirement_id")
        if not assignment.action_log:
            raise ValueError(f"需求 {assignment.requirement_id} 缺少确认动作")


def validate_import_batch(batch: ImportBatch) -> None:
    if not batch.batch_id:
        raise ValueError("导入批次缺少 batch_id")
    if not batch.imported_at:
        raise ValueError("导入批次缺少 imported_at")


def validate_team_insights(heatmap: list[HeatmapEntry], growth: list[GrowthSuggestion]) -> None:
    for entry in heatmap:
        if not entry.member:
            raise ValueError("负载热力图成员名称不能为空")
    for suggestion in growth:
        if not suggestion.member or not suggestion.suggestion:
            raise ValueError("成长建议缺少必要字段")
