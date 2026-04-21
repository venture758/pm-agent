<script setup>
import { ElTag, ElButton } from "element-plus";

defineProps({
  message: {
    type: Object,
    required: true,
  },
  isUser: {
    type: Boolean,
    default: false,
  },
  showGenerateAction: {
    type: Boolean,
    default: false,
  },
  canGenerate: {
    type: Boolean,
    default: false,
  },
  generating: {
    type: Boolean,
    default: false,
  },
});
const emit = defineEmits(["generate", "start-pipeline"]);

function priorityType(type) {
  const map = { 高: "danger", 中: "warning", 低: "info" };
  return map[type] || "info";
}

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function moduleLabel(req) {
  const bigModule = String(req?.big_module || "").trim();
  const functionModule = String(req?.function_module || "").trim();
  if (!bigModule || !functionModule) {
    return "";
  }
  return `${bigModule} / ${functionModule}`;
}

function isNeedsConfirmation(req) {
  return String(req?.match_status || "").toLowerCase() === "needs_confirmation";
}

function candidateLabel(candidate) {
  const bigModule = String(candidate?.big_module || "").trim();
  const functionModule = String(candidate?.function_module || "").trim();
  if (!bigModule || !functionModule) {
    return "";
  }
  return `${bigModule} / ${functionModule}`;
}
</script>

<template>
  <div class="message-bubble" :class="{ 'is-user': isUser, 'is-assistant': !isUser }">
    <div class="bubble-content">
      <template v-if="isUser">
        <span class="user-text">{{ message.content }}</span>
      </template>

      <template v-else>
        <p class="assistant-reply">{{ message.content }}</p>

        <div v-if="message.parsed_requirements?.length" class="requirements-summary">
          <div
            v-for="req in message.parsed_requirements"
            :key="req.requirement_id"
            class="requirement-card"
          >
            <div class="req-header">
              <strong class="req-title">{{ req.title }}</strong>
              <ElTag :type="priorityType(req.priority)" size="small">
                {{ req.priority }}
              </ElTag>
            </div>
            <div class="req-meta">
              <ElTag v-if="req.requirement_type" size="small" type="warning">
                {{ req.requirement_type }}
              </ElTag>
              <ElTag v-if="req.risk" :type="req.risk === '高' ? 'danger' : req.risk === '中' ? 'warning' : 'info'" size="small">
                风险: {{ req.risk }}
              </ElTag>
              <ElTag v-if="req.complexity" size="small" type="info">
                复杂度: {{ req.complexity }}
              </ElTag>
              <ElTag v-if="moduleLabel(req)" size="small" type="success">
                模块: {{ moduleLabel(req) }}
              </ElTag>
              <ElTag v-if="isNeedsConfirmation(req)" size="small" type="danger" effect="dark">
                待确认模块归属
              </ElTag>
            </div>
            <p v-if="req.abstract_summary" class="req-abstract">
              {{ req.abstract_summary }}
            </p>
            <div v-if="req.skills?.length" class="req-skills">
              <ElTag v-for="skill in req.skills" :key="skill" size="small" effect="plain">
                {{ skill }}
              </ElTag>
            </div>
            <div v-if="req.matched_module_keys?.length" class="req-modules">
              <span class="muted">关联模块: </span>
              <span v-for="key in req.matched_module_keys" :key="key" class="module-tag">{{ key }}</span>
            </div>
            <div v-if="req.blockers?.length" class="req-blockers">
              <span v-for="b in req.blockers" :key="b" class="blocker">⚠ {{ b }}</span>
            </div>
            <div v-if="asArray(req.match_evidence).length" class="req-evidence">
              <span class="muted">匹配依据: </span>
              <span v-for="evidence in asArray(req.match_evidence)" :key="evidence" class="evidence-tag">
                {{ evidence }}
              </span>
            </div>
            <div v-if="isNeedsConfirmation(req) && asArray(req.candidate_modules).length" class="req-candidates">
              <span class="muted">候选模块: </span>
              <span
                v-for="candidate in asArray(req.candidate_modules)"
                :key="`${candidate.big_module || ''}::${candidate.function_module || ''}`"
                class="candidate-tag"
              >
                {{ candidateLabel(candidate) || "未命名候选模块" }}
                <span v-if="candidate.reason" class="candidate-reason">（{{ candidate.reason }}）</span>
              </span>
            </div>
          </div>
        </div>

        <div v-if="showGenerateAction" class="bubble-action-bar">
          <ElButton
            type="primary"
            class="generate-inline-button"
            size="small"
            :disabled="!canGenerate || generating"
            :loading="generating"
            @click="emit('generate')"
          >
            {{ generating ? "生成中" : "生成推荐" }}
          </ElButton>
          <ElButton
            type="success"
            class="pipeline-inline-button"
            size="small"
            :disabled="generating"
            @click="emit('start-pipeline', 'auto')"
          >
            自动分析
          </ElButton>
          <ElButton
            class="pipeline-inline-button pipeline-inline-secondary"
            size="small"
            :disabled="generating"
            @click="emit('start-pipeline', 'manual')"
          >
            逐步确认
          </ElButton>
          <span class="bubble-action-hint">自动模式会连续执行，遇到待确认节点才暂停</span>
        </div>
      </template>
    </div>

    <span class="bubble-time">{{ message.timestamp?.slice(11, 16) || "" }}</span>
  </div>
</template>

<style scoped>
.message-bubble {
  display: flex;
  flex-direction: column;
  max-width: 80%;
  margin-bottom: 16px;
}
.message-bubble.is-user {
  align-self: flex-end;
  align-items: flex-end;
}
.message-bubble.is-assistant {
  align-self: flex-start;
  align-items: flex-start;
}
.bubble-content {
  padding: 10px 14px;
  border-radius: 12px;
  line-height: 1.6;
}
.is-user .bubble-content {
  background: #409eff;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.is-assistant .bubble-content {
  background: #f5f7fa;
  color: #303133;
  border-bottom-left-radius: 4px;
}
.user-text {
  white-space: pre-wrap;
  word-break: break-word;
}
.assistant-reply {
  margin: 0 0 8px;
}
.requirements-summary {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.requirement-card {
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  padding: 8px 10px;
}
.req-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}
.req-title {
  font-size: 14px;
}
.req-meta,
.req-skills,
.req-modules,
.req-blockers,
.req-evidence,
.req-candidates {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 4px;
}
.req-abstract {
  margin: 6px 0 2px;
  font-size: 12px;
  color: #475569;
  line-height: 1.5;
}
.module-tag {
  font-size: 12px;
  color: #606266;
}
.muted {
  font-size: 12px;
  color: #909399;
}
.blocker {
  font-size: 12px;
  color: #e6a23c;
}
.evidence-tag {
  font-size: 12px;
  color: #334155;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  padding: 0 8px;
}
.candidate-tag {
  font-size: 12px;
  color: #1e3a8a;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  border-radius: 999px;
  padding: 0 8px;
}
.candidate-reason {
  color: #64748b;
}
.bubble-time {
  font-size: 11px;
  color: #c0c4cc;
  margin-top: 2px;
}

.bubble-action-bar {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.generate-inline-button {
  border-radius: 999px;
}

.pipeline-inline-button {
  border-radius: 999px;
}

.bubble-action-hint {
  font-size: 12px;
  color: #647789;
}
</style>
