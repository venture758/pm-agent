<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useWorkspaceStore } from "../stores/workspace";

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

    <!-- Tab bar -->
    <div class="tab-bar">
      <button
        class="tab-item"
        :class="{ 'tab-item--active': activeTab === 'recommendations' }"
        data-test="tab-recommendations"
        @click="setActiveTab('recommendations')"
      >
        <svg class="tab-icon" viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <path d="M3 4h14M3 10h14M3 16h10" />
        </svg>
        推荐分配
        <span v-if="recommendations.length" class="tab-count">{{ recommendations.length }}</span>
      </button>
      <button
        class="tab-item"
        :class="{ 'tab-item--active': activeTab === 'history' }"
        data-test="tab-history"
        @click="setActiveTab('history')"
      >
        <svg class="tab-icon" viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="10" cy="10" r="7" />
          <path d="M10 6v4l3 2" />
        </svg>
        确认历史
        <span v-if="workspaceStore.confirmationHistory.total" class="tab-count tab-count--muted">{{ workspaceStore.confirmationHistory.total }}</span>
      </button>
    </div>

    <!-- ====== Tab: Recommendations ====== -->
    <div v-show="activeTab === 'recommendations'" class="tab-content">
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

<script>
import { computed, onMounted, ref } from "vue";
import { useWorkspaceStore } from "../stores/workspace";

const ConfirmationHistoryPanel = {
  name: "ConfirmationHistoryPanel",
  setup() {
    const workspaceStore = useWorkspaceStore();
    const expandedSessions = ref(new Set());

    const historyItems = computed(() => workspaceStore.confirmationHistory.items || []);
    const pagination = computed(() => ({
      page: workspaceStore.confirmationHistory.page || 1,
      pageSize: workspaceStore.confirmationHistory.page_size || 20,
      total: workspaceStore.confirmationHistory.total || 0,
      totalPages: workspaceStore.confirmationHistory.total_pages || 0,
    }));

    function toggleExpand(sessionId) {
      if (expandedSessions.value.has(sessionId)) {
        expandedSessions.value.delete(sessionId);
      } else {
        expandedSessions.value.add(sessionId);
      }
    }

    function isExpanded(sessionId) {
      return expandedSessions.value.has(sessionId);
    }

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

    function goToPage(page) {
      if (page < 1 || page > pagination.value.totalPages) return;
      workspaceStore.loadConfirmationHistory(page);
      expandedSessions.value.clear();
    }

    function refreshHistory() {
      workspaceStore.loadConfirmationHistory(pagination.value.page);
    }

    onMounted(() => {
      workspaceStore.loadConfirmationHistory(1);
    });

    return {
      workspaceStore,
      expandedSessions,
      historyItems,
      pagination,
      toggleExpand,
      isExpanded,
      formatTime,
      goToPage,
      refreshHistory,
    };
  },
  template: `
    <section class="history-panel">
      <!-- History header -->
      <article class="history-header">
        <div class="history-header-content">
          <div>
            <p class="history-kicker">Archive</p>
            <h3 class="history-title">确认历史</h3>
          </div>
          <div class="history-actions">
            <span class="history-stat">{{ pagination.total }} 条记录</span>
            <button class="history-refresh" :disabled="workspaceStore.loading" @click="refreshHistory">
              <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M2 8a6 6 0 0 1 10.47-4M14 8a6 6 0 0 1-10.47 4"/>
                <path d="M12 1v3h-3M4 15v-3h3"/>
              </svg>
              刷新
            </button>
          </div>
        </div>
        <p class="history-hint">查看已确认的分配记录，按确认时间倒序排列。</p>
      </article>

      <!-- History table -->
      <article v-if="historyItems.length" class="history-table-wrap">
        <table class="history-table">
          <thead>
            <tr>
              <th class="h-col-expand"></th>
              <th class="h-col-time">确认时间</th>
              <th class="h-col-session">Session ID</th>
              <th class="h-col-count">确认数</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="item in historyItems" :key="item.session_id">
              <tr class="h-summary-row" @click="toggleExpand(item.session_id)">
                <td class="h-col-expand">
                  <svg class="h-chevron" :class="{ expanded: isExpanded(item.session_id) }" viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M7 5l5 5-5 5" />
                  </svg>
                </td>
                <td class="h-col-time">{{ formatTime(item.created_at) }}</td>
                <td class="h-col-session">{{ item.session_id }}</td>
                <td class="h-col-count">
                  <span class="h-count-badge">{{ item.confirmed_count }}</span>
                </td>
              </tr>
              <tr v-if="isExpanded(item.session_id)" class="h-detail-row">
                <td :colspan="4">
                  <div class="h-detail-panel">
                    <table class="h-detail-table">
                      <thead>
                        <tr>
                          <th>需求 ID</th>
                          <th>标题</th>
                          <th>开发负责人</th>
                          <th>测试负责人</th>
                          <th>B角</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-for="assignment in item.confirmed_assignments" :key="assignment.requirement_id">
                          <td class="h-detail-id">{{ assignment.requirement_id }}</td>
                          <td class="h-detail-title">{{ assignment.title }}</td>
                          <td class="h-detail-owner">{{ assignment.development_owner }}</td>
                          <td class="h-detail-owner">{{ assignment.testing_owner || "—" }}</td>
                          <td class="h-detail-owner">{{ assignment.backup_owner || "—" }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </article>

      <!-- Pagination -->
      <div v-if="pagination.totalPages > 1" class="h-pagination">
        <button class="h-page-btn" :disabled="pagination.page <= 1" @click="goToPage(pagination.page - 1)">上一页</button>
        <span class="h-page-info">{{ pagination.page }} / {{ pagination.totalPages }}</span>
        <button class="h-page-btn" :disabled="pagination.page >= pagination.totalPages" @click="goToPage(pagination.page + 1)">下一页</button>
      </div>

      <!-- Empty state -->
      <article v-else class="h-empty">
        <svg viewBox="0 0 64 64" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="12" y="8" width="40" height="48" rx="4" />
          <path d="M22 20h20M22 28h20M22 36h12" />
        </svg>
        <h4>暂无确认记录</h4>
        <p>还没有确认过任何推荐分配。</p>
      </article>
    </section>
  `,
  styles: `
  `,
};
</script>

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

/* ====== Tab bar ====== */
.tab-bar {
  display: flex;
  align-items: flex-end;
  gap: 0;
  margin-top: 16px;
  border-bottom: 2px solid #eef1f5;
  padding: 0 4px;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 20px;
  border: none;
  background: transparent;
  color: #627284;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  position: relative;
  transition: color 0.2s ease;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
}

.tab-item:hover {
  color: #213a4f;
}

.tab-item--active {
  color: #17202a;
  border-bottom-color: #ba5c3d;
}

.tab-icon {
  opacity: 0.6;
  transition: opacity 0.2s ease;
}

.tab-item--active .tab-icon {
  opacity: 1;
  color: #ba5c3d;
}

.tab-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: rgba(186, 92, 61, 0.12);
  color: #ba5c3d;
}

.tab-count--muted {
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

/* ====== History Panel ====== */
.history-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.history-header {
  padding: 16px 20px;
  background: linear-gradient(135deg, rgba(238, 245, 255, 0.96) 0%, rgba(255, 255, 255, 0.94) 100%);
  border-radius: 20px;
  border: 1px solid rgba(23, 32, 42, 0.08);
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.08);
}

.history-header-content {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 6px;
}

.history-kicker {
  margin: 0;
  font-size: 11px;
  font-weight: 700;
  color: #8a9bab;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.history-title {
  margin: 0;
  font-size: 20px;
  font-family: Georgia, "Times New Roman", serif;
  color: #17202a;
  letter-spacing: 0.01em;
}

.history-actions {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.history-stat {
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
}

.history-refresh {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid rgba(23, 32, 42, 0.12);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.9);
  color: #213a4f;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.history-refresh:hover:not(:disabled) {
  background: rgba(255, 255, 255, 1);
  box-shadow: 0 2px 8px rgba(28, 46, 64, 0.08);
}

.history-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.history-hint {
  margin: 0;
  font-size: 12px;
  color: #8a9bab;
  line-height: 1.5;
}

/* History table */
.history-table-wrap {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 8px 28px rgba(28, 46, 64, 0.06);
}

.history-table {
  width: 100%;
  border-collapse: collapse;
}

.history-table thead tr {
  background: rgba(33, 58, 79, 0.04);
  border-bottom: 1px solid rgba(23, 32, 42, 0.08);
}

.history-table th {
  padding: 10px 16px;
  font-size: 11px;
  font-weight: 700;
  color: #627284;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.h-summary-row {
  border-bottom: 1px solid rgba(23, 32, 42, 0.06);
  cursor: pointer;
  transition: background 0.15s ease;
}

.h-summary-row:hover {
  background: rgba(33, 58, 79, 0.03);
}

.h-summary-row td {
  padding: 12px 16px;
  font-size: 13px;
  color: #17202a;
}

.h-col-expand {
  width: 36px;
  text-align: center !important;
}

.h-col-time {
  width: 150px;
  white-space: nowrap;
}

.h-col-session {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  color: #4b5b6b;
}

.h-col-count {
  width: 70px;
  text-align: center !important;
}

.h-count-badge {
  display: inline-block;
  min-width: 22px;
  padding: 2px 8px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 700;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
  text-align: center;
}

.h-chevron {
  transition: transform 0.2s ease;
  color: #8a9bab;
}

.h-chevron.expanded {
  transform: rotate(90deg);
}

/* History detail row */
.h-detail-row td {
  padding: 0;
  background: rgba(245, 248, 252, 0.6);
}

.h-detail-panel {
  padding: 14px 18px;
}

.h-detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

.h-detail-table thead tr {
  border-bottom: 1px solid rgba(23, 32, 42, 0.08);
}

.h-detail-table th {
  padding: 7px 10px;
  font-weight: 700;
  color: #627284;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
}

.h-detail-table td {
  padding: 7px 10px;
  border-bottom: 1px solid rgba(23, 32, 42, 0.04);
}

.h-detail-id {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 11px;
  color: #8a9bab;
}

.h-detail-title {
  color: #17202a;
  font-weight: 500;
}

.h-detail-owner {
  color: #4b5b6b;
}

/* History pagination */
.h-pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.h-page-btn {
  padding: 7px 18px;
  border-radius: 10px;
  border: 1px solid rgba(23, 32, 42, 0.12);
  background: rgba(255, 255, 255, 0.94);
  color: #17202a;
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.h-page-btn:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.06);
  border-color: rgba(23, 32, 42, 0.2);
}

.h-page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.h-page-info {
  font-size: 12px;
  color: #8a9bab;
  font-weight: 500;
}

/* History empty */
.h-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 48px 20px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
  text-align: center;
}

.h-empty svg {
  color: #c6d0dc;
  opacity: 0.6;
}

.h-empty h4 {
  margin: 0;
  font-size: 16px;
  font-family: Georgia, "Times New Roman", serif;
  color: #17202a;
}

.h-empty p {
  margin: 0;
  font-size: 13px;
  color: #8a9bab;
}

@media (max-width: 1180px) {
  .expand-actions {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .expand-details {
    grid-template-columns: 1fr;
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

  .expand-actions,
  .expand-details {
    grid-template-columns: 1fr;
  }

  .tab-bar {
    overflow-x: auto;
  }

  .tab-item {
    padding: 10px 14px;
    font-size: 13px;
    white-space: nowrap;
  }
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
