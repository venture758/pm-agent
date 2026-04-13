<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";

import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();
const actions = reactive({});

const searchKeyword = ref("");
const moduleFilter = ref("");
const ownerFilter = ref("");
const statusFilter = ref("all");
const sortBy = ref("confidence_desc");

const selectedIds = ref([]);
const isMobileReadonly = ref(false);

const batchAction = reactive({
  action: "accept",
  development_owner: "",
  testing_owner: "",
  backup_owner: "",
});

const recommendations = computed(() => workspaceStore.workspace.recommendations || []);
const recommendationMap = computed(() => {
  const map = {};
  recommendations.value.forEach((item) => {
    map[item.requirement_id] = item;
  });
  return map;
});

const moduleOptions = computed(() =>
  [...new Set(recommendations.value.map((item) => item.module_name || "未命中").filter(Boolean))].sort(),
);
const ownerOptions = computed(() =>
  [...new Set(recommendations.value.map((item) => item.development_owner || "").filter(Boolean))].sort(),
);

const overview = computed(() => {
  const total = recommendations.value.length;
  const unassigned = recommendations.value.filter((item) => item.unassigned_reason).length;
  const avgConfidence = recommendations.value.length
    ? recommendations.value.reduce((sum, item) => sum + Number(item.confidence || 0), 0) / recommendations.value.length
    : 0;
  return {
    total,
    active: recommendations.value.length,
    unassigned,
    selected: selectedIds.value.length,
    avgConfidence,
  };
});

const visibleRows = computed(() => {
  const keyword = searchKeyword.value.trim().toLowerCase();
  const rows = recommendations.value.map((item) => ({
    recommendation: item,
    id: item.requirement_id,
  }));

  const filtered = rows.filter((row) => {
    if (moduleFilter.value && (row.recommendation.module_name || "未命中") !== moduleFilter.value) {
      return false;
    }
    if (ownerFilter.value && (row.recommendation.development_owner || "") !== ownerFilter.value) {
      return false;
    }
    if (statusFilter.value === "unassigned" && !row.recommendation.unassigned_reason) {
      return false;
    }
    if (statusFilter.value === "assigned" && row.recommendation.unassigned_reason) {
      return false;
    }
    if (!keyword) {
      return true;
    }
    const matchedText = [
      row.id,
      row.recommendation.title || "",
      row.recommendation.module_name || "",
      row.recommendation.development_owner || "",
      row.recommendation.testing_owner || "",
      row.recommendation.backup_owner || "",
    ]
      .join(" ")
      .toLowerCase();
    return matchedText.includes(keyword);
  });

  const sorted = [...filtered];
  sorted.sort((left, right) => {
    if (sortBy.value === "title_asc") {
      return String(left.recommendation.title || "").localeCompare(String(right.recommendation.title || ""), "zh-Hans-CN");
    }
    if (sortBy.value === "module_asc") {
      return String(left.recommendation.module_name || "").localeCompare(String(right.recommendation.module_name || ""), "zh-Hans-CN");
    }
    if (sortBy.value === "owner_asc") {
      return String(left.recommendation.development_owner || "").localeCompare(String(right.recommendation.development_owner || ""), "zh-Hans-CN");
    }
    return Number(right.recommendation.confidence || 0) - Number(left.recommendation.confidence || 0);
  });
  return sorted;
});

const selectableVisibleIds = computed(() => visibleRows.value.map((row) => row.id));
const allVisibleSelected = computed(
  () => selectableVisibleIds.value.length > 0 && selectableVisibleIds.value.every((id) => selectedIds.value.includes(id)),
);
const hasSelection = computed(() => selectedIds.value.length > 0);
const canSubmit = computed(
  () => !workspaceStore.loading && !isMobileReadonly.value && recommendations.value.length > 0,
);

function ensureAction(requirementId, recommendation) {
  if (!actions[requirementId]) {
    actions[requirementId] = {
      action: "accept",
      development_owner: recommendation.development_owner,
      testing_owner: recommendation.testing_owner,
      backup_owner: recommendation.backup_owner,
      split_suggestion: recommendation.split_suggestion || "",
      collaborators_text: (recommendation.collaborators || []).join(", "),
    };
  }
  return actions[requirementId];
}

function syncMobileReadonly() {
  if (typeof window === "undefined") {
    isMobileReadonly.value = false;
    return;
  }
  isMobileReadonly.value = window.innerWidth <= 860;
}

function resetFilters() {
  searchKeyword.value = "";
  moduleFilter.value = "";
  ownerFilter.value = "";
  statusFilter.value = "all";
  sortBy.value = "confidence_desc";
}

function toggleSelectVisible(checked) {
  if (isMobileReadonly.value) return;
  if (!checked) {
    selectedIds.value = selectedIds.value.filter((id) => !selectableVisibleIds.value.includes(id));
    return;
  }
  selectedIds.value = [...new Set([...selectedIds.value, ...selectableVisibleIds.value])];
}

function toggleSelectRow(requirementId, checked) {
  if (isMobileReadonly.value) return;
  if (checked) {
    selectedIds.value = [...new Set([...selectedIds.value, requirementId])];
    return;
  }
  selectedIds.value = selectedIds.value.filter((id) => id !== requirementId);
}

async function markDeleted(requirementId) {
  if (isMobileReadonly.value) return;
  await workspaceStore.deleteRecommendation(requirementId);
  selectedIds.value = selectedIds.value.filter((id) => id !== requirementId);
}

async function batchDeleteSelected() {
  if (isMobileReadonly.value || !selectedIds.value.length) return;
  const ids = [...selectedIds.value];
  await workspaceStore.batchDeleteRecommendations(ids);
  selectedIds.value = [];
}

function applyBatchAction() {
  if (isMobileReadonly.value || !selectedIds.value.length) return;
  selectedIds.value.forEach((requirementId) => {
    const recommendation = recommendationMap.value[requirementId];
    if (!recommendation) return;
    const action = ensureAction(requirementId, recommendation);
    action.action = batchAction.action;
    if (batchAction.development_owner.trim()) {
      action.development_owner = batchAction.development_owner.trim();
    }
    if (batchAction.testing_owner.trim()) {
      action.testing_owner = batchAction.testing_owner.trim();
    }
    if (batchAction.backup_owner.trim()) {
      action.backup_owner = batchAction.backup_owner.trim();
    }
  });
}

async function submitConfirmations() {
  const payload = {};
  recommendations.value.forEach((recommendation) => {
    const action = ensureAction(recommendation.requirement_id, recommendation);
    payload[recommendation.requirement_id] = {
      action: action.action,
      development_owner: action.development_owner,
      testing_owner: action.testing_owner,
      backup_owner: action.backup_owner,
      split_suggestion: action.split_suggestion,
      collaborators: action.collaborators_text
        .split(",")
        .map((item) => item.trim())
        .filter(Boolean),
    };
  });
  await workspaceStore.confirmAssignments(payload);
  selectedIds.value = [];
}

watch(
  recommendations,
  (next) => {
    const available = new Set(next.map((item) => item.requirement_id));
    selectedIds.value = selectedIds.value.filter((id) => available.has(id));
  },
  { deep: true },
);

onMounted(() => {
  syncMobileReadonly();
  if (typeof window !== "undefined") {
    window.addEventListener("resize", syncMobileReadonly);
  }
});

onUnmounted(() => {
  if (typeof window !== "undefined") {
    window.removeEventListener("resize", syncMobileReadonly);
  }
});
</script>

<template>
  <section class="recommendations-page">
    <!-- Header with overview metrics -->
    <article class="rec-header">
      <div class="header-main">
        <div>
          <p class="section-kicker">Recommendation Console</p>
          <h2 class="page-title">推荐确认</h2>
        </div>
        <div class="header-actions">
          <span v-if="isMobileReadonly" class="soft-tag soft-tag-light">移动端仅浏览</span>
          <button
            class="primary-button"
            data-test="submit-confirm"
            :disabled="!canSubmit"
            @click="submitConfirmations"
          >
            提交确认
          </button>
        </div>
      </div>

      <p v-if="!recommendations.length" class="header-hint">先在需求输入页面生成推荐。</p>

      <div v-else class="metrics-row">
        <div class="metric">
          <span class="metric-label">总推荐</span>
          <span class="metric-value">{{ overview.total }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">待确认</span>
          <span class="metric-value warm">{{ overview.active }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">已选中</span>
          <span class="metric-value">{{ overview.selected }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">未分配</span>
          <span class="metric-value danger">{{ overview.unassigned }}</span>
        </div>
        <div class="metric">
          <span class="metric-label">平均置信度</span>
          <span class="metric-value">{{ overview.avgConfidence.toFixed(2) }}</span>
        </div>
      </div>
    </article>

    <!-- Toolbar -->
    <article v-if="recommendations.length" class="toolbar-card">
      <div class="toolbar-head">
        <h3>筛选与搜索</h3>
        <button class="ghost-btn" @click="resetFilters">重置</button>
      </div>
      <div class="toolbar-fields">
        <label class="field field-wide">
          <span>关键词</span>
          <input v-model="searchKeyword" placeholder="按需求标题、编号、模块、负责人检索" />
        </label>
        <label class="field">
          <span>模块</span>
          <select v-model="moduleFilter">
            <option value="">全部</option>
            <option v-for="moduleName in moduleOptions" :key="moduleName" :value="moduleName">{{ moduleName }}</option>
          </select>
        </label>
        <label class="field">
          <span>开发负责人</span>
          <select v-model="ownerFilter">
            <option value="">全部</option>
            <option v-for="owner in ownerOptions" :key="owner" :value="owner">{{ owner }}</option>
          </select>
        </label>
        <label class="field">
          <span>状态</span>
          <select v-model="statusFilter">
            <option value="all">全部</option>
            <option value="assigned">已分配</option>
            <option value="unassigned">未分配</option>
          </select>
        </label>
        <label class="field">
          <span>排序</span>
          <select v-model="sortBy">
            <option value="confidence_desc">按置信度</option>
            <option value="title_asc">按标题</option>
            <option value="module_asc">按模块</option>
            <option value="owner_asc">按负责人</option>
          </select>
        </label>
      </div>
      <p class="toolbar-count">当前显示 <strong>{{ visibleRows.length }}</strong> 条</p>
    </article>

    <!-- Batch operations -->
    <article v-if="recommendations.length && !isMobileReadonly" class="batch-card">
      <div class="batch-head">
        <h3>批量处理</h3>
        <label class="select-all">
          <input type="checkbox" :checked="allVisibleSelected" @change="toggleSelectVisible($event.target.checked)" />
          选中当前筛选结果
        </label>
      </div>
      <div class="batch-fields">
        <label class="field">
          <span>批量动作</span>
          <select v-model="batchAction.action" data-test="batch-action">
            <option value="accept">直接采纳</option>
            <option value="reassign">改派负责人</option>
            <option value="split">拆分需求</option>
            <option value="add-collaborator">添加协作人</option>
          </select>
        </label>
        <label class="field">
          <span>开发负责人</span>
          <input
            v-model="batchAction.development_owner"
            data-test="batch-dev-owner"
            placeholder="可选，留空不覆盖"
          />
        </label>
        <label class="field">
          <span>测试负责人</span>
          <input v-model="batchAction.testing_owner" placeholder="可选，留空不覆盖" />
        </label>
        <label class="field">
          <span>备选负责人</span>
          <input v-model="batchAction.backup_owner" placeholder="可选，留空不覆盖" />
        </label>
      </div>
      <div class="batch-actions">
        <button class="secondary-button" data-test="batch-apply" :disabled="!hasSelection" @click="applyBatchAction">
          应用到已选中（{{ selectedIds.length }}）
        </button>
        <button
          class="ghost-btn danger-text"
          data-test="batch-delete"
          :disabled="!hasSelection"
          @click="batchDeleteSelected"
        >
          删除已选中项
        </button>
      </div>
    </article>

    <!-- Recommendation cards -->
    <article v-if="recommendations.length" class="rec-list-area">
      <div v-if="!visibleRows.length" class="empty-state">当前筛选条件下无数据。</div>

      <div
        v-for="(row, idx) in visibleRows"
        :key="row.id"
        class="rec-card"
        :style="{ '--card-index': idx }"
      >
        <div class="rec-top">
          <div class="rec-title-area">
            <label v-if="!isMobileReadonly" class="rec-checkbox">
              <input
                type="checkbox"
                data-test="select-row"
                :checked="selectedIds.includes(row.id)"
                @change="toggleSelectRow(row.id, $event.target.checked)"
              />
            </label>
            <div class="rec-title-text">
              <h4>{{ row.recommendation.title }}</h4>
              <p class="rec-meta">
                需求 {{ row.id }} · 模块 {{ row.recommendation.module_name || "未命中" }} · 置信度 {{ Number(row.recommendation.confidence || 0).toFixed(2) }}
              </p>
            </div>
          </div>
          <div class="rec-tags">
            <span v-if="row.recommendation.unassigned_reason" class="soft-tag soft-tag-danger">未分配</span>
            <button v-if="!isMobileReadonly" class="ghost-btn sm" data-test="row-delete" @click="markDeleted(row.id)">
              删除
            </button>
          </div>
        </div>

        <!-- Action grid -->
        <div class="rec-actions">
          <label class="action-field">
            <span>动作</span>
            <select v-model="ensureAction(row.id, row.recommendation).action" :disabled="isMobileReadonly">
              <option value="accept">直接采纳</option>
              <option value="reassign">改派负责人</option>
              <option value="split">拆分需求</option>
              <option value="add-collaborator">添加协作人</option>
            </select>
          </label>
          <label class="action-field">
            <span>开发</span>
            <input v-model="ensureAction(row.id, row.recommendation).development_owner" :disabled="isMobileReadonly" />
          </label>
          <label class="action-field">
            <span>测试</span>
            <input v-model="ensureAction(row.id, row.recommendation).testing_owner" :disabled="isMobileReadonly" />
          </label>
          <label class="action-field">
            <span>备选</span>
            <input v-model="ensureAction(row.id, row.recommendation).backup_owner" :disabled="isMobileReadonly" />
          </label>
          <label class="action-field action-wide">
            <span>协作人</span>
            <input v-model="ensureAction(row.id, row.recommendation).collaborators_text" :disabled="isMobileReadonly" placeholder="张三, 李四" />
          </label>
          <label class="action-field action-wide">
            <span>拆分建议</span>
            <input v-model="ensureAction(row.id, row.recommendation).split_suggestion" :disabled="isMobileReadonly" />
          </label>
        </div>

        <!-- Collapsible details -->
        <div class="rec-details">
          <details class="detail-group">
            <summary>推荐依据（{{ row.recommendation.reasons?.length || 0 }}）</summary>
            <ul class="reason-list">
              <li v-for="reason in row.recommendation.reasons" :key="reason">{{ reason }}</li>
              <li v-if="row.recommendation.unassigned_reason">{{ row.recommendation.unassigned_reason }}</li>
            </ul>
          </details>
          <details class="detail-group">
            <summary>负载快照</summary>
            <div v-if="Object.keys(row.recommendation.workload_snapshot || {}).length" class="snapshot-list">
              <div v-for="(value, member) in row.recommendation.workload_snapshot" :key="member" class="snapshot-row">
                <span>{{ member }}</span>
                <strong>{{ Number(value).toFixed(2) }}</strong>
              </div>
            </div>
            <p v-else class="rec-empty">暂无负载快照。</p>
          </details>
        </div>
      </div>
    </article>
  </section>
</template>

<style scoped>
.recommendations-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: pageFadeIn 0.35s ease both;
}

@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(6px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Header */
.rec-header {
  padding: 22px 24px;
  background: linear-gradient(135deg, rgba(255, 249, 238, 0.96) 0%, rgba(255, 255, 255, 0.94) 100%);
  border-radius: 24px;
  border: 1px solid rgba(23, 32, 42, 0.08);
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.08);
}

.header-main {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 8px;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-family: Georgia, "Times New Roman", serif;
  letter-spacing: 0.01em;
  color: #17202a;
}

.header-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
  margin-top: 6px;
}

.header-hint {
  margin: 0;
  font-size: 13px;
  color: #8a9bab;
}

/* Metrics row */
.metrics-row {
  display: flex;
  gap: 12px;
  margin-top: 16px;
  flex-wrap: wrap;
}

.metric {
  flex: 1 1 120px;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.72);
  border: 1px solid rgba(23, 32, 42, 0.06);
}

.metric-label {
  font-size: 11px;
  color: #8a9bab;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  font-weight: 600;
}

.metric-value {
  font-size: 24px;
  font-weight: 700;
  color: #17202a;
  line-height: 1.2;
  margin-top: 4px;
}

.metric-value.warm {
  color: #ba5c3d;
}

.metric-value.danger {
  color: #8a1f28;
}

/* Toolbar card */
.toolbar-card {
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
}

.toolbar-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.toolbar-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #17202a;
  font-family: Georgia, "Times New Roman", serif;
}

.toolbar-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field span {
  font-size: 12px;
  color: #627284;
  font-weight: 600;
}

.field-wide {
  grid-column: 1 / -1;
}

.toolbar-count {
  margin: 12px 0 0;
  font-size: 12px;
  color: #8a9bab;
}

.toolbar-count strong {
  color: #17202a;
}

/* Batch card */
.batch-card {
  padding: 20px 24px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
}

.batch-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.batch-head h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #17202a;
  font-family: Georgia, "Times New Roman", serif;
}

.select-all {
  font-size: 12px;
  color: #627284;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  cursor: pointer;
}

.batch-fields {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.batch-actions {
  margin-top: 14px;
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

/* Recommendation list area */
.rec-list-area {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.rec-card {
  padding: 20px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 22px;
  box-shadow: 0 10px 32px rgba(28, 46, 64, 0.06);
  animation: cardFadeIn 0.3s ease both;
  animation-delay: calc(var(--card-index, 0) * 0.06s);
  transition: box-shadow 0.2s ease;
}

.rec-card:hover {
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.1);
}

.rec-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.rec-title-area {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  min-width: 0;
}

.rec-checkbox {
  margin-top: 3px;
  flex-shrink: 0;
}

.rec-title-text {
  min-width: 0;
}

.rec-title-text h4 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #17202a;
  line-height: 1.35;
}

.rec-meta {
  margin: 4px 0 0;
  font-size: 12px;
  color: #8a9bab;
  line-height: 1.4;
}

.rec-tags {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

/* Action fields */
.rec-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 12px;
}

.action-field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.action-field span {
  font-size: 11px;
  color: #8a9bab;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.action-wide {
  grid-column: 1 / -1;
}

/* Details */
.rec-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.detail-group {
  border: 1px solid #e8edf3;
  border-radius: 14px;
  padding: 10px 14px;
  background: #fafbfc;
}

.detail-group summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #213a4f;
}

.detail-group[open] summary {
  margin-bottom: 8px;
}

.reason-list {
  margin: 0;
  padding-left: 16px;
  color: #4b5b6b;
  font-size: 13px;
  line-height: 1.6;
  list-style: disc;
}

.snapshot-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.snapshot-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 10px;
  background: #fff;
  font-size: 13px;
  color: #4b5b6b;
}

.snapshot-row strong {
  color: #17202a;
  font-size: 13px;
}

.rec-empty {
  margin: 6px 0 0;
  font-size: 12px;
  color: #a0b0c0;
}

/* Buttons & utilities */
.ghost-btn {
  border: none;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
  border-radius: 999px;
  padding: 7px 16px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.ghost-btn:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.14);
}

.ghost-btn.sm {
  padding: 4px 12px;
  font-size: 11px;
  border-radius: 999px;
}

.ghost-btn.danger-text {
  background: transparent;
  color: #8a1f28;
}

.ghost-btn.danger-text:hover:not(:disabled) {
  background: rgba(138, 31, 40, 0.06);
}

.empty-state {
  padding: 32px 20px;
  text-align: center;
  color: #8a9bab;
  font-size: 14px;
}

@media (max-width: 1180px) {
  .metrics-row {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .toolbar-fields,
  .batch-fields,
  .rec-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .header-main {
    flex-direction: column;
  }

  .metrics-row {
    flex-direction: column;
  }

  .toolbar-fields,
  .batch-fields,
  .rec-actions,
  .rec-details {
    grid-template-columns: 1fr;
  }

  .rec-top {
    flex-direction: column;
  }
}
</style>
