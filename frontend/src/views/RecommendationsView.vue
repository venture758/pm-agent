<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useWorkspaceStore } from "../stores/workspace";
import ConfirmationHistoryPanel from "../components/ConfirmationHistoryPanel.vue";

const route = useRoute();
const router = useRouter();
const workspaceStore = useWorkspaceStore();
const actions = reactive({});

function normalizeTab(tab) {
  const rawTab = Array.isArray(tab) ? tab[0] : tab;
  return rawTab === "history" ? "history" : "recommendations";
}

const activeTab = ref(normalizeTab(route.query.tab));

const searchKeyword = ref("");
const moduleFilter = ref("");
const ownerFilter = ref("");
const statusFilter = ref("all");
const sortBy = ref("confidence_desc");

const selectedIds = ref([]);
const isMobileReadonly = ref(false);

const recommendations = computed(() => workspaceStore.workspace.recommendations || []);
const latestKnowledgeUpdate = computed(() => workspaceStore.workspace.latest_knowledge_update || null);
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

function formatTime(isoString) {
  if (!isoString) return "";
  const d = new Date(isoString);
  return d.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function knowledgeUpdateStatusLabel(status) {
  return {
    success: "已完成",
    skipped: "已跳过",
    failed: "失败",
  }[status] || "未知";
}

function knowledgeUpdateStatusClass(status) {
  return {
    success: "knowledge-status--success",
    skipped: "knowledge-status--skipped",
    failed: "knowledge-status--failed",
  }[status] || "knowledge-status--skipped";
}

function familiaritySuggestionCount(record) {
  const familiarity = record?.knowledge_updates?.suggested_familiarity;
  return Array.isArray(familiarity) ? familiarity.length : 0;
}

function suggestedModuleCount(record) {
  const modules = record?.knowledge_updates?.suggested_modules;
  return Array.isArray(modules) ? modules.length : 0;
}

function optimizationSuggestionCount(record) {
  return Array.isArray(record?.optimization_suggestions) ? record.optimization_suggestions.length : 0;
}

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

const expandedRows = ref(new Set());

function toggleExpand(id) {
  if (expandedRows.value.has(id)) {
    expandedRows.value.delete(id);
  } else {
    expandedRows.value.add(id);
  }
}

function confClass(confidence) {
  const val = Number(confidence || 0);
  if (val >= 0.8) return "conf-high";
  if (val >= 0.6) return "conf-mid";
  return "conf-low";
}

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

function syncTabQuery(tab) {
  const routeTab = Array.isArray(route.query.tab) ? route.query.tab[0] : route.query.tab;
  if ((tab === "history" && routeTab === "history") || (tab === "recommendations" && routeTab == null)) {
    return;
  }

  const nextQuery = { ...route.query };
  if (tab === "history") {
    nextQuery.tab = "history";
  } else {
    delete nextQuery.tab;
  }

  router.replace({
    name: "recommendations",
    params: { workspaceId: route.params.workspaceId || "default" },
    query: nextQuery,
  });
}

function setActiveTab(tab) {
  const normalized = normalizeTab(tab);
  if (activeTab.value === normalized) {
    return;
  }
  activeTab.value = normalized;
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

const activeFilterCount = computed(() => {
  let n = 0;
  if (searchKeyword.value.trim()) n++;
  if (moduleFilter.value) n++;
  if (ownerFilter.value) n++;
  if (statusFilter.value !== "all") n++;
  return n;
});

watch(
  recommendations,
  (next) => {
    const available = new Set(next.map((item) => item.requirement_id));
    selectedIds.value = selectedIds.value.filter((id) => available.has(id));
  },
  { deep: true },
);

watch(
  () => route.query.tab,
  (tab) => {
    const normalized = normalizeTab(tab);
    if (activeTab.value !== normalized) {
      activeTab.value = normalized;
    }
  },
);

watch(activeTab, (tab) => {
  syncTabQuery(tab);
});

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
    <!-- Page head with tab bar -->
    <div class="page-head">
      <div class="page-head-left">
        <p class="section-kicker">Confirmation Center</p>
        <h2 class="page-title">确认中心</h2>
      </div>
      <div class="head-right">
        <span v-if="isMobileReadonly" class="soft-tag soft-tag-light">移动端仅浏览</span>
        <span v-if="recommendations.length && activeTab === 'recommendations'" class="rec-count-badge">{{ recommendations.length }} 条推荐</span>
        <button
          v-if="activeTab === 'recommendations'"
          class="submit-btn"
          data-test="submit-confirm"
          :disabled="!canSubmit"
          @click="submitConfirmations"
        >
          提交确认
        </button>
      </div>
    </div>

    <!-- Sub-navigation bar -->
    <div class="sub-nav">
      <button
        class="sub-nav-link"
        :class="{ 'sub-nav-link--active': activeTab === 'recommendations' }"
        data-test="tab-recommendations"
        @click="setActiveTab('recommendations')"
      >
        <svg class="sub-nav-icon" viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 4h14M3 10h14M3 16h10" />
        </svg>
        推荐分配
        <span v-if="recommendations.length" class="sub-nav-count">{{ recommendations.length }}</span>
      </button>
      <span class="sub-nav-sep">/</span>
      <button
        class="sub-nav-link"
        :class="{ 'sub-nav-link--active': activeTab === 'history' }"
        @click="setActiveTab('history')"
      >
        <svg class="sub-nav-icon" viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="10" cy="10" r="7" />
          <path d="M10 6v4l3 2" />
        </svg>
        确认历史
        <span v-if="workspaceStore.confirmationHistory.total" class="sub-nav-count sub-nav-count--muted">{{ workspaceStore.confirmationHistory.total }}</span>
      </button>
    </div>

    <!-- ====== Tab: Recommendations ====== -->
    <div v-show="activeTab === 'recommendations'" class="tab-content">
      <article
        v-if="latestKnowledgeUpdate"
        class="knowledge-update-card"
        data-test="latest-knowledge-update"
      >
        <div class="knowledge-update-head">
          <div>
            <p class="knowledge-kicker">Knowledge Update</p>
            <h3 class="knowledge-title">最近一次知识更新</h3>
          </div>
          <span
            class="knowledge-status"
            :class="knowledgeUpdateStatusClass(latestKnowledgeUpdate.status)"
          >
            {{ knowledgeUpdateStatusLabel(latestKnowledgeUpdate.status) }}
          </span>
        </div>
        <p class="knowledge-meta">
          Session {{ latestKnowledgeUpdate.session_id || "—" }}
          <span v-if="latestKnowledgeUpdate.triggered_at"> · {{ formatTime(latestKnowledgeUpdate.triggered_at) }}</span>
        </p>
        <p class="knowledge-summary">
          {{
            latestKnowledgeUpdate.reply
              || (latestKnowledgeUpdate.status === "failed"
                ? "知识更新分析执行失败，请查看失败原因。"
                : latestKnowledgeUpdate.status === "skipped"
                  ? "当前未执行知识更新分析。"
                  : "知识更新分析已完成。")
          }}
        </p>
        <div class="knowledge-metrics">
          <span class="knowledge-metric">熟悉度建议 {{ familiaritySuggestionCount(latestKnowledgeUpdate) }}</span>
          <span class="knowledge-metric">模块建议 {{ suggestedModuleCount(latestKnowledgeUpdate) }}</span>
          <span class="knowledge-metric">优化建议 {{ optimizationSuggestionCount(latestKnowledgeUpdate) }}</span>
        </div>
        <p
          v-if="latestKnowledgeUpdate.status === 'failed' && latestKnowledgeUpdate.error_message"
          class="knowledge-error"
        >
          失败原因：{{ latestKnowledgeUpdate.error_message }}
        </p>
      </article>
      <p v-if="!recommendations.length" class="header-hint">先在需求输入页面生成推荐。</p>

      <!-- Command strip: search + filter chips -->
      <div v-if="recommendations.length" class="command-strip">
        <div class="strip-search">
          <svg class="strip-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            v-model="searchKeyword"
            type="text"
            class="strip-input"
            placeholder="搜索标题、编号、模块、负责人…"
          />
        </div>

        <div class="strip-chips">
          <div class="chip-dropdown">
            <button class="chip-btn" :class="{ 'chip-btn--active': moduleFilter }">
              <span class="chip-label">模块</span>
              <span class="chip-value">{{ moduleFilter || '全部' }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': !moduleFilter }" @click="moduleFilter = ''">全部</button>
              <button
                v-for="moduleName in moduleOptions"
                :key="moduleName"
                class="chip-menu-item"
                :class="{ 'chip-menu-item--active': moduleFilter === moduleName }"
                @click="moduleFilter = moduleName"
              >
                {{ moduleName }}
              </button>
            </div>
          </div>

          <div class="chip-dropdown">
            <button class="chip-btn" :class="{ 'chip-btn--active': ownerFilter }">
              <span class="chip-label">负责人</span>
              <span class="chip-value">{{ ownerFilter || '全部' }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': !ownerFilter }" @click="ownerFilter = ''">全部</button>
              <button
                v-for="owner in ownerOptions"
                :key="owner"
                class="chip-menu-item"
                :class="{ 'chip-menu-item--active': ownerFilter === owner }"
                @click="ownerFilter = owner"
              >
                {{ owner }}
              </button>
            </div>
          </div>

          <div class="chip-dropdown">
            <button class="chip-btn" :class="{ 'chip-btn--active': statusFilter !== 'all' }">
              <span class="chip-label">状态</span>
              <span class="chip-value">{{ { all: '全部', assigned: '已分配', unassigned: '未分配' }[statusFilter] }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': statusFilter === 'all' }" @click="statusFilter = 'all'">全部</button>
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': statusFilter === 'assigned' }" @click="statusFilter = 'assigned'">已分配</button>
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': statusFilter === 'unassigned' }" @click="statusFilter = 'unassigned'">未分配</button>
            </div>
          </div>

          <div class="chip-dropdown">
            <button class="chip-btn chip-btn--sort">
              <span class="chip-label">排序</span>
              <span class="chip-value">{{ { confidence_desc: '置信度', title_asc: '标题', module_asc: '模块', owner_asc: '负责人' }[sortBy] }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': sortBy === 'confidence_desc' }" @click="sortBy = 'confidence_desc'">按置信度</button>
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': sortBy === 'title_asc' }" @click="sortBy = 'title_asc'">按标题</button>
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': sortBy === 'module_asc' }" @click="sortBy = 'module_asc'">按模块</button>
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': sortBy === 'owner_asc' }" @click="sortBy = 'owner_asc'">按负责人</button>
            </div>
          </div>

          <span v-if="moduleFilter" class="filter-badge">
            {{ moduleFilter }}
            <button class="filter-badge-x" @click="moduleFilter = ''">×</button>
          </span>
          <span v-if="ownerFilter" class="filter-badge">
            {{ ownerFilter }}
            <button class="filter-badge-x" @click="ownerFilter = ''">×</button>
          </span>
          <span v-if="statusFilter !== 'all'" class="filter-badge">
            {{ { assigned: '已分配', unassigned: '未分配' }[statusFilter] }}
            <button class="filter-badge-x" @click="statusFilter = 'all'">×</button>
          </span>

          <button
            v-if="activeFilterCount > 0"
            class="strip-reset"
            @click="resetFilters"
          >
            清除筛选
          </button>
        </div>
      </div>

      <!-- Result count bar -->
      <div v-if="recommendations.length" class="count-bar">
        <span class="count-text">{{ visibleRows.length }} / {{ recommendations.length }} 条</span>
        <span v-if="overview.unassigned > 0" class="count-warn">
          <svg viewBox="0 0 16 16" width="14" height="14" fill="currentColor"><circle cx="8" cy="8" r="7" fill="none" stroke="currentColor" stroke-width="1.5"/><line x1="8" y1="5" x2="8" y2="9" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/><circle cx="8" cy="11.5" r="0.8"/></svg>
          {{ overview.unassigned }} 未分配
        </span>
      </div>

      <!-- Recommendation table -->
      <article v-if="recommendations.length" class="rec-table-area">
        <div v-if="!visibleRows.length" class="empty-state">当前筛选条件下无数据。</div>

        <div v-else class="table-frame">
          <table class="rec-table">
            <thead>
              <tr>
                <th class="th th--id">需求编号</th>
                <th class="th th--title">标题</th>
                <th class="th th--module">模块</th>
                <th class="th th--conf">置信度</th>
                <th class="th th--owner">开发</th>
                <th class="th th--owner">测试</th>
                <th class="th th--status">状态</th>
                <th class="th th--action">操作</th>
              </tr>
            </thead>
            <tbody>
              <template
                v-for="(row, idx) in visibleRows"
                :key="row.id"
              >
                <tr
                  class="tr"
                  :style="{ '--row-index': idx }"
                  :class="{ 'tr--unassigned': !!row.recommendation.unassigned_reason }"
                >
                  <td class="td td--id">{{ row.id }}</td>
                  <td class="td td--title">
                    <span class="title-text">{{ row.recommendation.title }}</span>
                    <button class="expand-btn" @click="toggleExpand(row.id)">
                      {{ expandedRows.has(row.id) ? '收起' : '展开' }}
                    </button>
                  </td>
                  <td class="td td--module">{{ row.recommendation.module_name || "未命中" }}</td>
                  <td class="td td--conf">
                    <span class="conf-pill" :class="confClass(row.recommendation.confidence)">
                      {{ Number(row.recommendation.confidence || 0).toFixed(2) }}
                    </span>
                  </td>
                  <td class="td td--owner">{{ row.recommendation.development_owner || "—" }}</td>
                  <td class="td td--owner">{{ row.recommendation.testing_owner || "—" }}</td>
                  <td class="td td--status">
                    <span v-if="row.recommendation.unassigned_reason" class="tag-unassigned">未分配</span>
                    <span v-else class="tag-assigned">已分配</span>
                  </td>
                  <td class="td td--action">
                    <button class="ghost-btn sm" data-test="row-delete" @click="markDeleted(row.id)">删除</button>
                  </td>
                </tr>
                <tr v-if="expandedRows.has(row.id)" class="tr-expand" :key="`${row.id}-expand`">
                  <td :colspan="8">
                    <div class="expand-body">
                      <div class="expand-actions">
                        <label class="ef">
                          <span>动作</span>
                          <select v-model="ensureAction(row.id, row.recommendation).action" :disabled="isMobileReadonly">
                            <option value="accept">直接采纳</option>
                            <option value="reassign">改派负责人</option>
                            <option value="split">拆分需求</option>
                            <option value="add-collaborator">添加协作人</option>
                          </select>
                        </label>
                        <label class="ef">
                          <span>开发负责人</span>
                          <input v-model="ensureAction(row.id, row.recommendation).development_owner" :disabled="isMobileReadonly" />
                        </label>
                        <label class="ef">
                          <span>测试负责人</span>
                          <input v-model="ensureAction(row.id, row.recommendation).testing_owner" :disabled="isMobileReadonly" />
                        </label>
                        <label class="ef">
                          <span>备选负责人</span>
                          <input v-model="ensureAction(row.id, row.recommendation).backup_owner" :disabled="isMobileReadonly" />
                        </label>
                        <label class="ef ef--wide">
                          <span>协作人</span>
                          <input v-model="ensureAction(row.id, row.recommendation).collaborators_text" :disabled="isMobileReadonly" placeholder="张三, 李四" />
                        </label>
                        <label class="ef ef--wide">
                          <span>拆分建议</span>
                          <input v-model="ensureAction(row.id, row.recommendation).split_suggestion" :disabled="isMobileReadonly" />
                        </label>
                      </div>

                      <div class="expand-details">
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
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </article>
    </div>

    <!-- ====== Tab: Confirmation History ====== -->
    <div v-show="activeTab === 'history'" class="tab-content">
      <ConfirmationHistoryPanel />
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;600;700&display=swap');

.recommendations-page {
  display: flex;
  flex-direction: column;
  gap: 0;
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

/* ====== Page head ====== */
.page-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 4px 0 0 0;
}

.page-head-left {
  display: flex;
  flex-direction: column;
}

.page-title {
  margin: 0;
  font-size: 28px;
  font-family: Georgia, "Times New Roman", serif;
  letter-spacing: 0.01em;
  color: #17202a;
  line-height: 1.1;
}

.head-right {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  flex-shrink: 0;
}

.rec-count-badge {
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
}

.submit-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 9px 28px;
  border: none;
  border-radius: 999px;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  background: #ba5c3d;
  color: #fff;
  box-shadow: 0 4px 14px rgba(186, 92, 61, 0.18);
  transition: all 0.2s ease;
}

.submit-btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(186, 92, 61, 0.25);
}

.submit-btn:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

/* ====== Sub-navigation bar ====== */
.sub-nav {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 14px;
  padding: 6px 14px;
  border-radius: 12px;
  background: rgba(33, 58, 79, 0.03);
  width: fit-content;
}

.sub-nav-link {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border: none;
  background: transparent;
  color: #8a9bab;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border-radius: 8px;
  transition: all 0.15s ease;
}

.sub-nav-link:hover {
  color: #213a4f;
  background: rgba(33, 58, 79, 0.06);
}

.sub-nav-link--active {
  color: #17202a;
  background: #fff;
  box-shadow: 0 1px 4px rgba(28, 46, 64, 0.06);
}

.sub-nav-link--active .sub-nav-icon {
  color: #ba5c3d;
}

.sub-nav-icon {
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.sub-nav-link--active .sub-nav-icon {
  opacity: 1;
}

.sub-nav-sep {
  color: #c8d1da;
  font-size: 13px;
  font-weight: 600;
  user-select: none;
}

.sub-nav-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 700;
  background: rgba(186, 92, 61, 0.12);
  color: #ba5c3d;
}

.sub-nav-count--muted {
  background: rgba(33, 58, 79, 0.08);
  color: #627284;
}

/* Tab content */
.tab-content {
  padding-top: 16px;
  animation: tabFadeIn 0.3s ease both;
}

@keyframes tabFadeIn {
  from { opacity: 0; transform: translateY(4px); }
  to { opacity: 1; transform: translateY(0); }
}

.header-hint {
  margin: 0;
  font-size: 13px;
  color: #8a9bab;
  padding: 8px 0;
}

.knowledge-update-card {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 18px 20px;
  margin-bottom: 14px;
  border-radius: 18px;
  border: 1px solid rgba(23, 32, 42, 0.08);
  background:
    radial-gradient(circle at top right, rgba(186, 92, 61, 0.14), transparent 34%),
    linear-gradient(135deg, rgba(255, 251, 247, 0.96), rgba(255, 255, 255, 0.94));
  box-shadow: 0 14px 36px rgba(28, 46, 64, 0.08);
}

.knowledge-update-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.knowledge-kicker {
  margin: 0 0 4px;
  font-size: 11px;
  font-weight: 700;
  color: #8a9bab;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.knowledge-title {
  margin: 0;
  font-size: 20px;
  font-family: Georgia, "Times New Roman", serif;
  color: #17202a;
}

.knowledge-status {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.knowledge-status--success {
  background: rgba(56, 127, 90, 0.12);
  color: #2b6c49;
}

.knowledge-status--skipped {
  background: rgba(33, 58, 79, 0.08);
  color: #5a6d80;
}

.knowledge-status--failed {
  background: rgba(186, 92, 61, 0.12);
  color: #a54b30;
}

.knowledge-meta,
.knowledge-summary,
.knowledge-error {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.knowledge-meta {
  color: #7d8d9c;
}

.knowledge-summary {
  color: #213a4f;
}

.knowledge-error {
  color: #a54b30;
}

.knowledge-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.knowledge-metric {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #4f6476;
  background: rgba(33, 58, 79, 0.06);
}

/* ====== Command Strip ====== */
.command-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  background: #1a2636;
  border-radius: 14px;
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.strip-search {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 200px;
  position: relative;
}

.strip-icon {
  color: rgba(244, 241, 235, 0.35);
  flex-shrink: 0;
}

.strip-input {
  width: 100%;
  border: none;
  background: transparent;
  color: #f4f1eb;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 14px;
  padding: 6px 0;
  outline: none;
}

.strip-input::placeholder {
  color: rgba(244, 241, 235, 0.3);
}

.strip-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

/* Chip button (dropdown trigger) */
.chip-dropdown {
  position: relative;
}

.chip-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(244, 241, 235, 0.6);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.chip-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
}

.chip-btn--active {
  background: rgba(186, 92, 61, 0.2);
  border-color: rgba(186, 92, 61, 0.35);
  color: #e4a882;
}

.chip-btn--sort {
  border-style: dashed;
}

.chip-label {
  opacity: 0.6;
}

.chip-value {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-arrow {
  opacity: 0.4;
  flex-shrink: 0;
}

/* Dropdown menu */
.chip-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 10;
  min-width: 160px;
  max-height: 240px;
  overflow-y: auto;
  background: #1e3040;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
  padding: 4px;
  display: none;
}

.chip-dropdown:hover .chip-menu {
  display: block;
}

.chip-menu-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: rgba(244, 241, 235, 0.7);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s ease;
}

.chip-menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.chip-menu-item--active {
  background: rgba(186, 92, 61, 0.2);
  color: #e4a882;
}

/* Filter badge */
.filter-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(228, 189, 121, 0.15);
  color: #e4bd79;
  font-size: 11px;
  font-weight: 700;
}

.filter-badge-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #e4bd79;
  font-size: 14px;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0.7;
  line-height: 1;
}

.filter-badge-x:hover {
  opacity: 1;
}

/* Reset button */
.strip-reset {
  padding: 5px 10px;
  border: 1px dashed rgba(244, 241, 235, 0.15);
  border-radius: 8px;
  background: transparent;
  color: rgba(244, 241, 235, 0.4);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.strip-reset:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(244, 241, 235, 0.7);
  border-color: rgba(244, 241, 235, 0.25);
}

/* ====== Count bar ====== */
.count-bar {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 6px 4px;
}

.count-text {
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 700;
  color: #627284;
  letter-spacing: 0.02em;
}

.count-warn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #ba5c3d;
}

/* ====== Table Frame ====== */
.table-frame {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(28, 46, 64, 0.04);
}

.rec-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  min-width: 1200px;
}

.rec-table thead th {
  position: sticky;
  top: 0;
  z-index: 2;
}

.th {
  padding: 9px 12px;
  text-align: left;
  border-bottom: 2px solid #eef1f5;
  background: #fafbfc;
  color: #627284;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  user-select: none;
  white-space: nowrap;
}

.th--id { width: 80px; }
.th--conf { width: 80px; }
.th--status { width: 70px; }
.th--action { width: 70px; }

.tr {
  transition: background 0.12s ease;
}

.tr:hover {
  background: rgba(255, 248, 235, 0.3);
}

.tr--unassigned {
  background: rgba(186, 92, 61, 0.02);
}

.tr--unassigned:hover {
  background: rgba(255, 248, 235, 0.4);
}

.td {
  padding: 8px 12px;
  border-bottom: 1px solid #f3f5f8;
  font-size: 13px;
  color: #17202a;
  white-space: nowrap;
  vertical-align: middle;
}

.rec-table tbody tr:last-child .td {
  border-bottom: none;
}

.td--id {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  color: #4b5b6b;
}

.td--title {
  max-width: 280px;
  white-space: normal;
}

.td--module {
  max-width: 150px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.td--conf {
  text-align: center;
}

.td--action {
  text-align: center;
}

/* Expand button */
.expand-btn {
  display: inline-block;
  margin-left: 8px;
  border: none;
  background: rgba(33, 58, 79, 0.06);
  color: #627284;
  border-radius: 6px;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  vertical-align: middle;
}

.expand-btn:hover {
  background: rgba(33, 58, 79, 0.12);
  color: #213a4f;
}

/* Confidence pill */
.conf-pill {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 700;
}

.conf-high {
  background: rgba(58, 138, 92, 0.1);
  color: #2a6b48;
}

.conf-mid {
  background: rgba(186, 140, 61, 0.12);
  color: #8a6630;
}

.conf-low {
  background: rgba(138, 31, 40, 0.1);
  color: #8a1f28;
}

/* Status tags */
.tag-unassigned {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(186, 92, 61, 0.1);
  color: #ba5c3d;
}

.tag-assigned {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
  background: rgba(58, 138, 92, 0.1);
  color: #2a6b48;
}

/* Expanded row */
.tr-expand {
  background: #fafbfc;
}

.tr-expand td {
  border-bottom: 1px solid #eef1f5;
  padding: 0;
}

.expand-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px;
}

.expand-actions {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
}

.expand-details {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

/* Expand form fields */
.ef {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.ef span {
  font-size: 11px;
  color: #8a9bab;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.ef input,
.ef select {
  border: 1px solid #e8edf3;
  border-radius: 8px;
  padding: 6px 10px;
  font-size: 13px;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  color: #17202a;
  background: #fff;
  outline: none;
  transition: border-color 0.15s ease;
}

.ef input:focus,
.ef select:focus {
  border-color: #ba5c3d;
}

.ef input:disabled,
.ef select:disabled {
  background: #f5f7fa;
  color: #8a9bab;
  cursor: not-allowed;
}

.ef--wide {
  grid-column: 1 / -1;
}

/* Detail group */
.expand-details .detail-group {
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #e8edf3;
  border-radius: 14px;
}

.expand-details .detail-group summary {
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: #213a4f;
}

.expand-details .detail-group[open] summary {
  margin-bottom: 8px;
}

.expand-details .reason-list {
  margin: 0;
  padding-left: 16px;
  color: #4b5b6b;
  font-size: 13px;
  line-height: 1.6;
  list-style: disc;
}

.expand-details .snapshot-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.expand-details .snapshot-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 10px;
  border-radius: 10px;
  background: #fafbfc;
  font-size: 13px;
  color: #4b5b6b;
}

.expand-details .snapshot-row strong {
  color: #17202a;
  font-size: 13px;
}

.rec-table-area .rec-empty {
  margin: 6px 0 0;
  font-size: 12px;
  color: #a0b0c0;
}

/* ====== Recommendation cards ====== */
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
  .rec-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .page-head {
    flex-direction: column;
  }

  .command-strip {
    flex-direction: column;
    align-items: stretch;
  }

  .strip-chips {
    justify-content: flex-start;
  }

  .rec-actions,
  .rec-details {
    grid-template-columns: 1fr;
  }

  .rec-top {
    flex-direction: column;
  }
}
</style>
