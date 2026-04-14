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

function goToPage(page) {
  if (page < 1 || page > pagination.value.totalPages) return;
  workspaceStore.loadConfirmationHistory(page);
  expandedSessions.value.clear();
}

onMounted(() => {
  workspaceStore.loadConfirmationHistory(1);
});
</script>

<template>
  <section class="confirmation-history-page">
    <!-- Header -->
    <article class="history-header">
      <div class="header-content">
        <div>
          <p class="section-kicker">Confirmation History</p>
          <h2 class="page-title">确认历史</h2>
        </div>
        <div class="header-actions">
          <span class="stat-tag">{{ pagination.total }} 条记录</span>
          <button class="secondary-button" :disabled="workspaceStore.loading" @click="workspaceStore.loadConfirmationHistory(pagination.page)">
            刷新
          </button>
        </div>
      </div>
      <p class="header-hint">查看已确认的分配记录，按确认时间倒序排列。</p>
    </article>

    <!-- Table -->
    <article v-if="historyItems.length" class="history-table-wrap">
      <table class="history-table">
        <thead>
          <tr>
            <th class="col-expand"></th>
            <th class="col-time">确认时间</th>
            <th class="col-session">Session ID</th>
            <th class="col-count">确认数</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="item in historyItems" :key="item.session_id">
            <tr class="summary-row" @click="toggleExpand(item.session_id)">
              <td class="col-expand">
                <svg class="chevron" :class="{ expanded: isExpanded(item.session_id) }" viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M7 5l5 5-5 5" />
                </svg>
              </td>
              <td class="col-time">{{ formatTime(item.created_at) }}</td>
              <td class="col-session">{{ item.session_id }}</td>
              <td class="col-count">
                <span class="count-badge">{{ item.confirmed_count }}</span>
              </td>
            </tr>
            <tr v-if="isExpanded(item.session_id)" class="detail-row">
              <td :colspan="4">
                <div class="detail-panel">
                  <table class="detail-table">
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
                        <td class="detail-id">{{ assignment.requirement_id }}</td>
                        <td class="detail-title">{{ assignment.title }}</td>
                        <td class="detail-owner">{{ assignment.development_owner }}</td>
                        <td class="detail-owner">{{ assignment.testing_owner || "—" }}</td>
                        <td class="detail-owner">{{ assignment.backup_owner || "—" }}</td>
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
    <div v-if="pagination.totalPages > 1" class="pagination-bar">
      <button class="page-btn" :disabled="pagination.page <= 1" @click="goToPage(pagination.page - 1)">上一页</button>
      <span class="page-info">{{ pagination.page }} / {{ pagination.totalPages }}</span>
      <button class="page-btn" :disabled="pagination.page >= pagination.totalPages" @click="goToPage(pagination.page + 1)">下一页</button>
    </div>

    <!-- Empty state -->
    <article v-else class="empty-card">
      <svg viewBox="0 0 64 64" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
        <rect x="12" y="8" width="40" height="48" rx="4" />
        <path d="M22 20h20M22 28h20M22 36h12" />
      </svg>
      <h3>暂无确认记录</h3>
      <p>还没有确认过任何推荐分配。</p>
    </article>
  </section>
</template>

<style scoped>
.confirmation-history-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: pageFadeIn 0.35s ease both;
}

@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* Header */
.history-header {
  padding: 22px 24px;
  background: linear-gradient(135deg, rgba(238, 245, 255, 0.96) 0%, rgba(255, 255, 255, 0.94) 100%);
  border-radius: 24px;
  border: 1px solid rgba(23, 32, 42, 0.08);
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.08);
}

.header-content {
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
  flex-shrink: 0;
  margin-top: 6px;
}

.stat-tag {
  padding: 5px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
}

.header-hint {
  margin: 0;
  font-size: 13px;
  color: #8a9bab;
  line-height: 1.5;
}

/* Table */
.history-table-wrap {
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 8px 28px rgba(28, 46, 64, 0.06);
  overflow: hidden;
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
  padding: 12px 16px;
  font-size: 12px;
  font-weight: 600;
  color: #4b5b6b;
  text-align: left;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.summary-row {
  border-bottom: 1px solid rgba(23, 32, 42, 0.06);
  cursor: pointer;
  transition: background 0.15s ease;
}

.summary-row:hover {
  background: rgba(33, 58, 79, 0.03);
}

.summary-row td {
  padding: 14px 16px;
  font-size: 14px;
  color: #17202a;
}

.col-expand {
  width: 36px;
  text-align: center !important;
}

.col-time {
  width: 160px;
  white-space: nowrap;
}

.col-session {
  font-family: "SF Mono", "Menlo", monospace;
  font-size: 13px;
  color: #4b5b6b;
}

.col-count {
  width: 80px;
  text-align: center !important;
}

.count-badge {
  display: inline-block;
  min-width: 24px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
  text-align: center;
}

.chevron {
  transition: transform 0.2s ease;
  color: #8a9bab;
}

.chevron.expanded {
  transform: rotate(90deg);
}

/* Detail row */
.detail-row td {
  padding: 0;
  background: rgba(245, 248, 252, 0.6);
}

.detail-panel {
  padding: 16px 20px;
}

.detail-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}

.detail-table thead tr {
  border-bottom: 1px solid rgba(23, 32, 42, 0.08);
}

.detail-table th {
  padding: 8px 12px;
  font-weight: 600;
  color: #4b5b6b;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  text-align: left;
}

.detail-table td {
  padding: 8px 12px;
  border-bottom: 1px solid rgba(23, 32, 42, 0.04);
}

.detail-id {
  font-family: "SF Mono", "Menlo", monospace;
  font-size: 12px;
  color: #8a9bab;
}

.detail-title {
  color: #17202a;
  font-weight: 500;
}

.detail-owner {
  color: #4b5b6b;
}

/* Pagination */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
}

.page-btn {
  padding: 8px 20px;
  border-radius: 12px;
  border: 1px solid rgba(23, 32, 42, 0.12);
  background: rgba(255, 255, 255, 0.94);
  color: #17202a;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
}

.page-btn:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.06);
  border-color: rgba(23, 32, 42, 0.2);
}

.page-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.page-info {
  font-size: 13px;
  color: #8a9bab;
  font-weight: 500;
}

/* Empty state */
.empty-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 60px 20px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
  text-align: center;
}

.empty-card svg {
  color: #c6d0dc;
  opacity: 0.6;
}

.empty-card h3 {
  margin: 0;
  font-size: 18px;
  font-family: Georgia, "Times New Roman", serif;
  color: #17202a;
}

.empty-card p {
  margin: 0;
  font-size: 14px;
  color: #8a9bab;
}

@media (max-width: 860px) {
  .header-content {
    flex-direction: column;
  }

  .col-time {
    width: 120px;
  }

  .detail-table {
    font-size: 12px;
  }

  .detail-table th,
  .detail-table td {
    padding: 6px 8px;
  }
}
</style>
