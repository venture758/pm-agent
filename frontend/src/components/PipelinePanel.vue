<script setup>
import { ref, computed } from "vue";
import { ElMessage, ElMessageBox, ElDialog } from "element-plus";
import { useWorkspaceStore } from "../stores/workspace";

const props = defineProps({
  pipelineState: {
    type: Object,
    default: null,
  },
});

const emit = defineEmits(["close", "complete"]);

const workspaceStore = useWorkspaceStore();
const modifyDialogVisible = ref(false);
const modifyData = ref("");

const STEP_ICONS = {
  completed: "✓",
  current: "▶",
  pending: "·",
};

const currentStepKey = computed(() => props.pipelineState?.current_step);
const isLastStep = computed(() => {
  const ps = props.pipelineState;
  if (!ps) return false;
  return ps.current_step_index >= ps.step_progress.length - 1;
});
const isLoading = computed(() => workspaceStore.loading);
const currentStepData = computed(() => {
  const ps = props.pipelineState;
  if (!ps || !ps.current_step) return {};
  const stepResult = ps.step_results?.[ps.current_step];
  // Data comes from the pipelineState top-level fields
  switch (ps.current_step) {
    case "requirement_parsing":
      return { requirements: ps.requirements || [] };
    case "personnel_matching":
      return { assignments: ps.assignment_suggestions || [] };
    case "module_extraction":
      return { module_changes: ps.module_changes || [] };
    case "team_analysis":
      return ps.team_analysis || {};
    case "knowledge_update":
      return { pending_changes: ps.pending_changes || [] };
    default:
      return {};
  }
});

function getStepIcon(step) {
  const result = props.pipelineState?.step_results?.[step.step];
  if (result) return "✓";
  if (step.status === "completed") return "✓";
  if (step.status === "current") return isLoading.value ? "⟳" : "▶";
  return "·";
}

function getStepClass(step) {
  if (step.status === "completed") return "step-completed";
  if (step.status === "current") return "step-current";
  return "step-pending";
}

async function handleConfirm() {
  const action = isLastStep.value ? "execute" : "confirm";
  try {
    const result = await workspaceStore.confirmPipelineStep(action);
    if (result.status === "complete") {
      ElMessage.success("分析完成");
      emit("complete");
    }
  } catch {
    // error handled by store
  }
}

async function handleSkip() {
  try {
    const result = await workspaceStore.confirmPipelineStep("skip");
    if (result.status === "complete") {
      ElMessage.success("分析完成");
      emit("complete");
    }
  } catch {
    // error handled by store
  }
}

async function handleReanalyze() {
  try {
    const { value: feedback } = await ElMessageBox.prompt(
      "请输入反馈约束，LLM 将根据您的意见重新生成当前步骤的结果",
      "重新分析",
      {
        confirmButtonText: "重新分析",
        cancelButtonText: "取消",
        inputPlaceholder: "例如：李祥这周不在，请调整人员分配",
      }
    );
    if (feedback) {
      const result = await workspaceStore.confirmPipelineStep("reanalyze", { feedback });
      if (result.status === "complete") {
        ElMessage.success("分析完成");
        emit("complete");
      }
    }
  } catch {
    // user cancelled
  }
}

function handleModify() {
  const data = JSON.stringify(currentStepData.value, null, 2);
  modifyData.value = data;
  modifyDialogVisible.value = true;
}

async function submitModify() {
  try {
    const parsed = JSON.parse(modifyData.value);
    modifyDialogVisible.value = false;
    const result = await workspaceStore.confirmPipelineStep("modify", { modifications: parsed });
    if (result.status === "complete") {
      ElMessage.success("分析完成");
      emit("complete");
    }
  } catch (e) {
    ElMessage.error("JSON 格式错误：" + e.message);
  }
}

function confidenceClass(confidence) {
  if (!confidence) return "";
  const val = typeof confidence === "number" ? confidence : parseFloat(confidence);
  if (val >= 0.8) return "confidence-high";
  if (val >= 0.5) return "confidence-medium";
  return "confidence-low";
}

function changeTypeLabel(changeType) {
  const labels = {
    "create_big_module": "新建大模块",
    "create_sub_module": "新建子模块",
    "update_owner": "更新负责人",
  };
  return labels[changeType] || changeType || "更新";
}

function countFamiliarityUpdates() {
  const changes = currentStepData.value.module_changes || [];
  return changes.filter(c => c.change_type === "update_owner" || c.familiarity_update).length;
}
</script>

<template>
  <div class="pipeline-panel">
    <!-- Header -->
    <div class="panel-header">
      <span class="panel-title">分析进度</span>
      <button class="close-btn" @click="emit('close')" title="关闭">
        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <line x1="18" y1="6" x2="6" y2="18" />
          <line x1="6" y1="6" x2="18" y2="18" />
        </svg>
      </button>
    </div>

    <!-- Progress Steps -->
    <div class="progress-steps">
      <div
        v-for="step in pipelineState?.step_progress || []"
        :key="step.step"
        class="pipeline-step"
        :class="getStepClass(step)"
      >
        <div class="step-icon">
          <span v-if="getStepIcon(step) === '⟳'" class="spinner"></span>
          <span v-else>{{ getStepIcon(step) }}</span>
        </div>
        <span class="step-label">{{ step.label }}</span>
      </div>
    </div>

    <!-- Loading indicator -->
    <div v-if="isLoading" class="loading-bar">
      <div class="loading-dots">
        <span></span><span></span><span></span>
      </div>
      <span class="loading-text">分析中...</span>
    </div>

    <!-- Step Result Area -->
    <div class="step-result" v-if="currentStepKey && !isLoading">
      <!-- Requirement Parsing -->
      <div v-if="currentStepKey === 'requirement_parsing'" class="result-section">
        <h4 class="result-title">需求解析结果</h4>
        <table class="data-table requirements-table">
          <thead>
            <tr>
              <th>标题</th>
              <th>优先级</th>
              <th>复杂度</th>
              <th>风险</th>
              <th>所需技能</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="req in currentStepData.requirements" :key="req.requirement_id">
              <td>{{ req.title }}</td>
              <td>{{ req.priority }}</td>
              <td>{{ req.complexity }}</td>
              <td>{{ req.risk }}</td>
              <td>
                <span v-for="skill in (req.skills || [])" :key="skill" class="skill-tag">{{ skill }}</span>
              </td>
            </tr>
          </tbody>
        </table>
        <p v-if="!currentStepData.requirements?.length" class="empty-hint">暂无需求数据</p>
      </div>

      <!-- Personnel Matching -->
      <div v-if="currentStepKey === 'personnel_matching'" class="result-section">
        <h4 class="result-title">人员匹配结果</h4>
        <div class="assignment-cards">
          <div
            v-for="assignment in currentStepData.assignments"
            :key="assignment.requirement_id"
            class="assignment-card"
          >
            <div class="card-title">{{ assignment.title || assignment.requirement_id }}</div>
            <div class="card-fields">
              <div class="field">
                <span class="field-label">开发负责人：</span>
                <span class="field-value">{{ assignment.developer || "—" }}</span>
              </div>
              <div class="field">
                <span class="field-label">测试人：</span>
                <span class="field-value">{{ assignment.tester || "—" }}</span>
              </div>
              <div class="field">
                <span class="field-label">B角：</span>
                <span class="field-value">{{ assignment.backup || "—" }}</span>
              </div>
              <div class="field">
                <span class="field-label">协作人：</span>
                <span class="field-value">{{ assignment.collaborators?.join("、") || "—" }}</span>
              </div>
              <div class="field">
                <span class="field-label">推荐理由：</span>
                <span class="field-value">{{ assignment.reason || "—" }}</span>
              </div>
              <div class="field">
                <span class="field-label">置信度：</span>
                <span class="confidence" :class="confidenceClass(assignment.confidence)">
                  {{ assignment.confidence || "—" }}
                </span>
              </div>
            </div>
          </div>
        </div>
        <p v-if="!currentStepData.assignments?.length" class="empty-hint">暂无匹配结果</p>
      </div>

      <!-- Module Extraction -->
      <div v-if="currentStepKey === 'module_extraction'" class="result-section">
        <h4 class="result-title">模块提炼结果</h4>
        <ul class="module-changes">
          <li
            v-for="(change, idx) in (currentStepData.module_changes || [])"
            :key="idx"
            class="change-item"
          >
            <span class="change-type" :class="`type-${change.change_type || 'update'}`">
              {{ changeTypeLabel(change.change_type) }}
            </span>
            <span class="module-name">{{ change.module_name || change.module_key }}</span>
            <span class="change-reason">{{ change.reason }}</span>
          </li>
        </ul>
        <p v-if="!currentStepData.module_changes?.length" class="empty-hint">暂无模块变更</p>
      </div>

      <!-- Team Analysis -->
      <div v-if="currentStepKey === 'team_analysis'" class="result-section">
        <h4 class="result-title">梯队分析结果</h4>
        <div v-if="currentStepData.single_points?.length" class="risk-section">
          <h5 class="sub-title">单点风险</h5>
          <table class="data-table risk-table">
            <thead>
              <tr>
                <th>模块</th>
                <th>风险成员</th>
                <th>严重程度</th>
                <th>建议</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="risk in currentStepData.single_points" :key="risk.module || risk.member">
                <td>{{ risk.module || "—" }}</td>
                <td>{{ risk.member || risk.members?.join("、") }}</td>
                <td>
                  <span class="severity" :class="`sev-${risk.severity}`">
                    {{ risk.severity }}
                  </span>
                </td>
                <td>{{ risk.suggestion }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-if="currentStepData.growth_suggestions?.length" class="growth-section">
          <h5 class="sub-title">成长路径</h5>
          <ul class="growth-list">
            <li v-for="g in currentStepData.growth_suggestions" :key="g.member" class="growth-item">
              <span class="growth-member">{{ g.member }}</span>
              <span class="growth-detail">{{ g.detail || g.suggestion }}</span>
            </li>
          </ul>
        </div>
        <p v-if="!currentStepData.single_points?.length && !currentStepData.growth_suggestions?.length" class="empty-hint">暂无分析结果</p>
      </div>

      <!-- Knowledge Update -->
      <div v-if="currentStepKey === 'knowledge_update'" class="result-section">
        <h4 class="result-title">知识更新 - 待执行变更</h4>
        <div class="summary-stats">
          <div class="stat-item">
            <span class="stat-value">{{ (pipelineState?.requirements || []).length }}</span>
            <span class="stat-label">需求解析数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ (pipelineState?.assignment_suggestions || []).length }}</span>
            <span class="stat-label">人员分配数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ (currentStepData.module_changes || []).length }}</span>
            <span class="stat-label">模块创建数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ countFamiliarityUpdates() }}</span>
            <span class="stat-label">熟悉度更新数</span>
          </div>
          <div class="stat-item">
            <span class="stat-value">{{ (currentStepData.single_points || []).length }}</span>
            <span class="stat-label">风险识别数</span>
          </div>
        </div>
        <ul class="pending-changes-list">
          <li v-for="(change, idx) in (currentStepData.pending_changes || [])" :key="idx" class="pending-change">
            {{ change.description || JSON.stringify(change) }}
          </li>
        </ul>
      </div>

      <!-- Reply text -->
      <p v-if="pipelineState?.reply" class="step-reply">{{ pipelineState.reply }}</p>
    </div>

    <!-- Action Buttons -->
    <div class="action-bar" :class="{ disabled: isLoading }">
      <button class="action-btn btn-confirm" :disabled="isLoading" @click="handleConfirm">
        {{ isLastStep ? "执行变更" : "确认" }}
      </button>
      <button class="action-btn btn-modify" :disabled="isLoading" @click="handleModify">修改</button>
      <button class="action-btn btn-reanalyze" :disabled="isLoading" @click="handleReanalyze">重新分析</button>
      <button class="action-btn btn-skip" :disabled="isLoading" @click="handleSkip">跳过</button>
    </div>

    <!-- Modify Dialog -->
    <ElDialog
      v-model="modifyDialogVisible"
      title="修改当前步骤数据"
      width="600px"
      :close-on-click-modal="false"
    >
      <p class="dialog-hint">以下为 JSON 格式，修改后点击"提交修改"。</p>
      <textarea
        v-model="modifyData"
        class="json-editor"
        spellcheck="false"
      ></textarea>
      <template #footer>
        <button class="dialog-btn btn-cancel" @click="modifyDialogVisible = false">取消</button>
        <button class="dialog-btn btn-primary" @click="submitModify">提交修改</button>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.pipeline-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: #fafafa;
  font-family: 'Source Sans 3', 'Noto Sans SC', -apple-system, sans-serif;
}

/* Header */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid #e8e8e8;
  background: #fff;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: #1a1a1a;
}

.close-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  padding: 4px;
  border-radius: 4px;
}

.close-btn:hover {
  background: #f0f0f0;
  color: #333;
}

/* Progress Steps */
.progress-steps {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  gap: 0;
  background: #fff;
  border-bottom: 1px solid #e8e8e8;
}

.pipeline-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex: 1;
  position: relative;
}

.pipeline-step:not(:last-child)::after {
  content: "";
  position: absolute;
  top: 14px;
  right: -50%;
  width: 100%;
  height: 2px;
  background: #e0e0e0;
  z-index: 0;
}

.pipeline-step.step-completed:not(:last-child)::after {
  background: #52c41a;
}

.step-icon {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  z-index: 1;
  background: #e8e8e8;
  color: #999;
}

.step-completed .step-icon {
  background: #52c41a;
  color: #fff;
}

.step-current .step-icon {
  background: #1890ff;
  color: #fff;
  box-shadow: 0 0 0 3px rgba(24, 144, 255, 0.2);
}

.step-label {
  font-size: 11px;
  color: #999;
  white-space: nowrap;
}

.step-completed .step-label {
  color: #52c41a;
}

.step-current .step-label {
  color: #1890ff;
  font-weight: 500;
}

.spinner {
  display: inline-block;
  width: 14px;
  height: 14px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: #fff;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Loading Bar */
.loading-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 16px;
  background: #fff;
}

.loading-dots {
  display: flex;
  gap: 4px;
}

.loading-dots span {
  width: 6px;
  height: 6px;
  background: #1890ff;
  border-radius: 50%;
  animation: bounce 1.2s infinite;
}

.loading-dots span:nth-child(2) { animation-delay: 0.2s; }
.loading-dots span:nth-child(3) { animation-delay: 0.4s; }

@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

.loading-text {
  font-size: 13px;
  color: #666;
}

/* Step Result */
.step-result {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.result-section {
  background: #fff;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}

.result-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin: 0 0 12px;
}

/* Data Tables */
.data-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.data-table th {
  text-align: left;
  padding: 6px 8px;
  background: #f5f5f5;
  font-weight: 500;
  color: #666;
  border-bottom: 1px solid #e8e8e8;
}

.data-table td {
  padding: 6px 8px;
  border-bottom: 1px solid #f0f0f0;
  color: #333;
  vertical-align: top;
}

.skill-tag {
  display: inline-block;
  padding: 1px 6px;
  background: #f0f5ff;
  color: #1890ff;
  border-radius: 3px;
  font-size: 11px;
  margin-right: 4px;
  margin-bottom: 2px;
}

/* Assignment Cards */
.assignment-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assignment-card {
  border: 1px solid #e8e8e8;
  border-radius: 6px;
  padding: 10px;
  background: #fafafa;
}

.card-title {
  font-size: 13px;
  font-weight: 600;
  color: #1a1a1a;
  margin-bottom: 8px;
}

.card-fields {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field {
  font-size: 12px;
  display: flex;
  gap: 4px;
}

.field-label {
  color: #888;
  flex-shrink: 0;
  min-width: 70px;
}

.field-value {
  color: #333;
}

.confidence {
  font-weight: 600;
}

.confidence-high { color: #52c41a; }
.confidence-medium { color: #faad14; }
.confidence-low { color: #ff4d4f; }

/* Module Changes */
.module-changes {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.change-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
}

.change-type {
  padding: 2px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  flex-shrink: 0;
}

.type-create_big_module {
  background: #e6f7ff;
  color: #1890ff;
}

.type-create_sub_module {
  background: #f6ffed;
  color: #52c41a;
}

.type-update_owner {
  background: #fff7e6;
  color: #fa8c16;
}

.module-name {
  font-weight: 500;
  color: #333;
}

.change-reason {
  color: #888;
  font-size: 11px;
}

/* Team Analysis */
.risk-section, .growth-section {
  margin-bottom: 16px;
}

.sub-title {
  font-size: 13px;
  font-weight: 500;
  color: #666;
  margin: 0 0 8px;
}

.severity {
  padding: 1px 6px;
  border-radius: 3px;
  font-size: 11px;
  font-weight: 500;
}

.sev-high {
  background: #fff1f0;
  color: #ff4d4f;
}

.sev-medium {
  background: #fffbe6;
  color: #faad14;
}

.sev-low {
  background: #f6ffed;
  color: #52c41a;
}

.growth-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.growth-item {
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
}

.growth-member {
  font-weight: 600;
  color: #1a1a1a;
  margin-right: 8px;
}

.growth-detail {
  color: #666;
}

/* Knowledge Update */
.summary-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: 8px;
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 8px;
  background: #f5f5f5;
  border-radius: 6px;
}

.stat-value {
  font-size: 18px;
  font-weight: 700;
  color: #1890ff;
}

.stat-label {
  font-size: 10px;
  color: #888;
  margin-top: 2px;
}

.pending-changes-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.pending-change {
  padding: 6px 0;
  border-bottom: 1px solid #f0f0f0;
  font-size: 12px;
  color: #666;
}

/* Reply text */
.step-reply {
  font-size: 12px;
  color: #888;
  margin: 8px 0 0;
  font-style: italic;
}

/* Empty hint */
.empty-hint {
  text-align: center;
  color: #bbb;
  font-size: 12px;
  padding: 16px;
}

/* Action Bar */
.action-bar {
  display: flex;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e8e8e8;
  background: #fff;
}

.action-bar.disabled {
  opacity: 0.6;
  pointer-events: none;
}

.action-btn {
  flex: 1;
  padding: 8px 0;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #fff;
  color: #333;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.action-btn:hover:not(:disabled) {
  border-color: #1890ff;
  color: #1890ff;
}

.action-btn:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.btn-confirm {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

.btn-confirm:hover:not(:disabled) {
  background: #40a9ff;
  border-color: #40a9ff;
  color: #fff;
}

.btn-modify:hover:not(:disabled) {
  border-color: #fa8c16;
  color: #fa8c16;
}

.btn-reanalyze:hover:not(:disabled) {
  border-color: #722ed1;
  color: #722ed1;
}

.btn-skip:hover:not(:disabled) {
  border-color: #ff4d4f;
  color: #ff4d4f;
}

/* Modify Dialog */
.dialog-hint {
  font-size: 12px;
  color: #888;
  margin: 0 0 8px;
}

.json-editor {
  width: 100%;
  min-height: 300px;
  padding: 12px;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  font-family: 'Menlo', 'Consolas', monospace;
  font-size: 12px;
  resize: vertical;
  outline: none;
}

.json-editor:focus {
  border-color: #1890ff;
}

.dialog-btn {
  padding: 8px 20px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid #d9d9d9;
  background: #fff;
  font-family: inherit;
}

.dialog-btn:hover {
  border-color: #1890ff;
  color: #1890ff;
}

.dialog-btn.btn-primary {
  background: #1890ff;
  border-color: #1890ff;
  color: #fff;
}

.dialog-btn.btn-primary:hover {
  background: #40a9ff;
  border-color: #40a9ff;
  color: #fff;
}

.dialog-btn.btn-cancel {
  margin-right: 8px;
}
</style>
