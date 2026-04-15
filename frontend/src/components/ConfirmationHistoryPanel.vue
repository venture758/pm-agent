<script setup>
import { computed, onMounted, ref } from "vue";
import { useWorkspaceStore } from "../stores/workspace";

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

function knowledgeUpdateStatusLabel(update) {
  const status = update?.status;
  return {
    success: "已完成",
    skipped: "已跳过",
    failed: "失败",
  }[status] || "未执行";
}

function knowledgeUpdateStatusClass(update) {
  const status = update?.status;
  return {
    success: "h-status--success",
    skipped: "h-status--skipped",
    failed: "h-status--failed",
  }[status] || "h-status--skipped";
}

function familiaritySuggestionCount(update) {
  const familiarity = update?.knowledge_updates?.suggested_familiarity;
  return Array.isArray(familiarity) ? familiarity.length : 0;
}

function suggestedModuleCount(update) {
  const modules = update?.knowledge_updates?.suggested_modules;
  return Array.isArray(modules) ? modules.length : 0;
}

function optimizationSuggestionCount(update) {
  return Array.isArray(update?.optimization_suggestions) ? update.optimization_suggestions.length : 0;
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
</script>

<template>
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

    <!-- History content -->
    <template v-if="historyItems.length">
      <article class="history-table-wrap">
      <table class="history-table">
        <thead>
          <tr>
            <th class="h-col-expand"></th>
            <th class="h-col-time">确认时间</th>
            <th class="h-col-session">Session ID</th>
            <th class="h-col-count">确认数</th>
            <th class="h-col-knowledge">知识更新</th>
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
              <td class="h-col-knowledge">
                <span
                  class="h-status-badge"
                  :class="knowledgeUpdateStatusClass(item.knowledge_update)"
                  data-test="history-knowledge-status"
                >
                  {{ knowledgeUpdateStatusLabel(item.knowledge_update) }}
                </span>
              </td>
            </tr>
            <tr v-if="isExpanded(item.session_id)" class="h-detail-row">
              <td :colspan="5">
                <div class="h-detail-panel">
                  <div class="h-knowledge-card">
                    <div class="h-knowledge-head">
                      <strong>知识更新</strong>
                      <span class="h-status-badge" :class="knowledgeUpdateStatusClass(item.knowledge_update)">
                        {{ knowledgeUpdateStatusLabel(item.knowledge_update) }}
                      </span>
                    </div>
                    <p class="h-knowledge-summary">
                      {{
                        item.knowledge_update?.reply
                          || (item.knowledge_update?.status === "failed"
                            ? "知识更新分析执行失败。"
                            : item.knowledge_update?.status === "skipped"
                              ? "当前会话未执行知识更新分析。"
                              : "当前会话暂无知识更新记录。")
                      }}
                    </p>
                    <div v-if="item.knowledge_update" class="h-knowledge-metrics">
                      <span class="h-knowledge-metric">熟悉度建议 {{ familiaritySuggestionCount(item.knowledge_update) }}</span>
                      <span class="h-knowledge-metric">模块建议 {{ suggestedModuleCount(item.knowledge_update) }}</span>
                      <span class="h-knowledge-metric">优化建议 {{ optimizationSuggestionCount(item.knowledge_update) }}</span>
                    </div>
                    <p
                      v-if="item.knowledge_update?.status === 'failed' && item.knowledge_update?.error_message"
                      class="h-knowledge-error"
                    >
                      失败原因：{{ item.knowledge_update.error_message }}
                    </p>
                  </div>
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
    </template>

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
</template>

<style scoped>
/* ====== Panel ====== */
.history-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ====== Header ====== */
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

/* ====== Table ====== */
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

.h-col-knowledge {
  width: 120px;
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

.h-status-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 72px;
  padding: 4px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
}

.h-status--success {
  background: rgba(56, 127, 90, 0.12);
  color: #2b6c49;
}

.h-status--skipped {
  background: rgba(33, 58, 79, 0.08);
  color: #5a6d80;
}

.h-status--failed {
  background: rgba(186, 92, 61, 0.12);
  color: #a54b30;
}

.h-chevron {
  transition: transform 0.2s ease;
  color: #8a9bab;
}

.h-chevron.expanded {
  transform: rotate(90deg);
}

/* Detail row */
.h-detail-row td {
  padding: 0;
  background: rgba(245, 248, 252, 0.6);
}

.h-detail-panel {
  padding: 14px 18px;
}

.h-knowledge-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px 16px;
  margin-bottom: 14px;
  border-radius: 14px;
  border: 1px solid rgba(23, 32, 42, 0.08);
  background: rgba(255, 255, 255, 0.92);
}

.h-knowledge-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.h-knowledge-summary,
.h-knowledge-error {
  margin: 0;
  font-size: 13px;
  line-height: 1.6;
}

.h-knowledge-summary {
  color: #3f5263;
}

.h-knowledge-error {
  color: #a54b30;
}

.h-knowledge-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.h-knowledge-metric {
  display: inline-flex;
  align-items: center;
  padding: 5px 9px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  color: #4f6476;
  background: rgba(33, 58, 79, 0.06);
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

/* Pagination */
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

/* Empty */
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
</style>
