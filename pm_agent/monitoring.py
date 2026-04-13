from __future__ import annotations

from datetime import date

from .config import BLOCKED_KEYWORDS, COMPLETE_STATUSES
from .models import AgentState, ExecutionAlert
from .utils import parse_date


def generate_execution_alerts(state: AgentState, today: date | None = None) -> list[ExecutionAlert]:
    today = today or date.today()
    alerts: list[ExecutionAlert] = []
    for story in state.stories.values():
        planned_date = parse_date(story.plan_test_date)
        if planned_date and planned_date < today and story.status not in COMPLETE_STATUSES:
            alerts.append(
                ExecutionAlert(
                    severity="高" if (today - planned_date).days >= 1 else "中",
                    reason=f"故事 {story.user_story_code} 已超过计划提测时间",
                    suggestion="建议检查开发进度，必要时重新分配或拆分需求。",
                    story_code=story.user_story_code,
                    context=[story.name, story.owner, story.status],
                )
            )
        if any(keyword in story.status for keyword in BLOCKED_KEYWORDS):
            alerts.append(
                ExecutionAlert(
                    severity="高",
                    reason=f"故事 {story.user_story_code} 状态显示阻塞",
                    suggestion="建议升级阻塞项并明确责任人。",
                    story_code=story.user_story_code,
                    context=[story.name, story.owner],
                )
            )
        if story.defects > 0:
            alerts.append(
                ExecutionAlert(
                    severity="中",
                    reason=f"故事 {story.user_story_code} 存在关联缺陷",
                    suggestion="建议安排回归验证并评估质量风险。",
                    story_code=story.user_story_code,
                    context=[story.name, f"缺陷数:{story.defects}"],
                )
            )
    for task in state.tasks.values():
        planned_end = parse_date(task.estimated_end)
        if planned_end and planned_end < today and task.status not in COMPLETE_STATUSES:
            alerts.append(
                ExecutionAlert(
                    severity="高" if (today - planned_end).days >= 1 else "中",
                    reason=f"任务 {task.task_code} 已超过预计结束时间",
                    suggestion="建议确认当前负责人进度，并考虑增加协作人或重排计划。",
                    task_code=task.task_code,
                    context=[task.story_name, task.owner, task.status],
                )
            )
        if any(keyword in task.status for keyword in BLOCKED_KEYWORDS):
            alerts.append(
                ExecutionAlert(
                    severity="高",
                    reason=f"任务 {task.task_code} 处于阻塞状态",
                    suggestion="建议立即梳理阻塞原因并推动解决。",
                    task_code=task.task_code,
                    context=[task.name, task.owner],
                )
            )
        if task.defects > 0:
            alerts.append(
                ExecutionAlert(
                    severity="中",
                    reason=f"任务 {task.task_code} 存在缺陷记录",
                    suggestion="建议结合缺陷数量判断是否需要增加测试或回归时间。",
                    task_code=task.task_code,
                    context=[task.name, f"缺陷数:{task.defects}"],
                )
            )
    return alerts
