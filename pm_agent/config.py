from __future__ import annotations

DEFAULT_MYSQL_DDL_PATH = "db/schema.mysql.ddl.sql"

WORKFLOW_CONFIGS = {
    "group_requirement_intake": {
        "required_fields": ["title", "priority", "source_url"],
        "description": "接收群消息或导入需求，并标准化为结构化需求。",
    },
    "module_knowledge_sync": {
        "required_fields": ["big_module", "function_module", "primary_owner", "backup_owners"],
        "description": "导入并维护模块知识库。",
    },
    "assignment_recommendation": {
        "required_fields": ["development_owner", "testing_owner", "backup_owner", "reasons"],
        "description": "基于知识库和成员负载生成需求分配建议。",
    },
    "assignment_confirmation": {
        "required_fields": ["action_log", "development_owner"],
        "description": "记录项目经理对分配建议的确认和调整动作。",
    },
    "excel_story_task_sync": {
        "required_fields": ["batch_id", "actions"],
        "description": "按故事编码和任务编号执行离线同步。",
    },
    "execution_monitoring": {
        "required_fields": ["severity", "reason", "suggestion"],
        "description": "根据每日导入的故事、任务和执行信号生成预警。",
    },
    "team_insight": {
        "required_fields": ["heatmap", "single_points", "growth_suggestions"],
        "description": "输出团队负载、单点依赖和成长建议。",
    },
}

PRIORITY_SCORES = {"低": 1, "中": 2, "高": 3}
COMPLEXITY_SCORES = {"低": 1, "中": 2, "中高": 3, "高": 4}
RISK_SCORES = {"低": 1, "中": 2, "高": 3}
FAMILIARITY_SCORES = {"不了解": 0, "了解": 2, "熟悉": 3}
COMPLETE_STATUSES = {"已完成", "完成", "主干测试完成", "已关闭"}
BLOCKED_KEYWORDS = ("阻塞", "卡住", "卡点")
QUALITY_KEYWORDS = ("缺陷", "回归", "质量", "异常")

# LLM (NVIDIA NIM API)
NVIDIA_NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"
#NVIDIA_NIM_DEFAULT_MODEL = "meta/llama-3.1-8b-instruct"
NVIDIA_NIM_DEFAULT_MODEL = "z-ai/glm4.7"
NVIDIA_NIM_DEFAULT_TEMPERATURE = 0.3
NVIDIA_NIM_DEFAULT_MAX_TOKENS = 20000
NVIDIA_NIM_API_KEY_ENV = "NVIDIA_NIM_API_KEY"
