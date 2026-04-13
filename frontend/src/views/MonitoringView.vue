<script setup>
import { computed, onMounted } from "vue";

import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();

const alertCount = computed(() => workspaceStore.monitoring.length);
const highSeverityCount = computed(() => workspaceStore.monitoring.filter((a) => a.severity === "高").length);

onMounted(() => {
  workspaceStore.refreshMonitoring();
});
</script>

<template>
  <section class="monitoring-page">
    <!-- Header -->
    <article class="monitoring-header">
      <div class="header-content">
        <div>
          <p class="section-kicker">Monitoring</p>
          <h2 class="page-title">执行预警</h2>
        </div>
        <div class="header-actions">
          <span v-if="highSeverityCount > 0" class="soft-tag soft-tag-danger">
            {{ highSeverityCount }} 条高危
          </span>
          <span class="stat-tag">{{ alertCount }} 条预警</span>
          <button class="secondary-button" :disabled="workspaceStore.loading" @click="workspaceStore.refreshMonitoring()">
            刷新
          </button>
        </div>
      </div>
      <p class="header-hint">监控执行异常，包括延期、阻塞和质量风险。</p>
    </article>

    <!-- Alert feed -->
    <article v-if="alertCount" class="alert-feed">
      <div
        v-for="alert in workspaceStore.monitoring"
        :key="`${alert.story_code}-${alert.task_code}-${alert.reason}`"
        class="alert-card"
        :class="`severity-${alert.severity}`"
      >
        <div class="alert-icon">
          <svg v-if="alert.severity === '高'" viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 3L1.5 17h17L10 3z" />
            <path d="M10 8v4M10 14.5v.5" />
          </svg>
          <svg v-else-if="alert.severity === '中'" viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
            <circle cx="10" cy="10" r="7" />
            <path d="M10 7v3.5M10 13v.5" />
          </svg>
          <svg v-else viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
            <circle cx="10" cy="10" r="7" />
            <path d="M10 10v.5" />
          </svg>
        </div>
        <div class="alert-body">
          <div class="alert-head">
            <h3>{{ alert.reason }}</h3>
            <span class="alert-code">{{ alert.story_code || alert.task_code || "未绑定编码" }}</span>
          </div>
          <p class="alert-suggestion">{{ alert.suggestion }}</p>
          <div class="alert-context" v-if="alert.context?.length">
            <span v-for="item in alert.context" :key="item" class="context-tag">{{ item }}</span>
          </div>
        </div>
      </div>
    </article>

    <!-- Empty state -->
    <article v-else class="empty-card">
      <svg viewBox="0 0 64 64" width="56" height="56" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="32" cy="32" r="24" />
        <path d="M22 32h20" />
        <path d="M32 22v20" />
      </svg>
      <h3>暂无预警</h3>
      <p>一切运行正常，没有检测到执行异常。</p>
    </article>
  </section>
</template>

<style scoped>
.monitoring-page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  animation: pageFadeIn 0.35s ease both;
}

@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

@keyframes alertSlideIn {
  from { opacity: 0; transform: translateX(-8px); }
  to { opacity: 1; transform: translateX(0); }
}

/* Header */
.monitoring-header {
  padding: 22px 24px;
  background: linear-gradient(135deg, rgba(255, 249, 238, 0.96) 0%, rgba(255, 255, 255, 0.94) 100%);
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
  flex-wrap: wrap;
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

/* Alert feed */
.alert-feed {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.alert-card {
  display: flex;
  gap: 16px;
  padding: 18px 20px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 8px 28px rgba(28, 46, 64, 0.06);
  border-left: 4px solid #8a9bab;
  animation: alertSlideIn 0.3s ease both;
  transition: box-shadow 0.2s ease, transform 0.15s ease;
}

.alert-card:hover {
  box-shadow: 0 12px 36px rgba(28, 46, 64, 0.1);
  transform: translateX(2px);
}

.alert-card.severity-高 {
  border-left-color: #8a1f28;
  background: rgba(255, 252, 251, 0.96);
}

.alert-card.severity-中 {
  border-left-color: #ba8c3d;
  background: rgba(255, 253, 247, 0.96);
}

.alert-card.severity-低 {
  border-left-color: #3a8a5c;
  background: rgba(251, 254, 252, 0.96);
}

.alert-icon {
  flex-shrink: 0;
  display: flex;
  align-items: flex-start;
  padding-top: 2px;
}

.alert-card.severity-高 .alert-icon {
  color: #8a1f28;
}

.alert-card.severity-中 .alert-icon {
  color: #ba8c3d;
}

.alert-card.severity-低 .alert-icon {
  color: #3a8a5c;
}

.alert-body {
  flex: 1;
  min-width: 0;
}

.alert-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.alert-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #17202a;
  line-height: 1.4;
}

.alert-code {
  font-size: 11px;
  color: #8a9bab;
  font-family: "SF Mono", "Menlo", monospace;
  flex-shrink: 0;
  margin-top: 3px;
}

.alert-suggestion {
  margin: 0 0 10px;
  font-size: 13px;
  color: #4b5b6b;
  line-height: 1.55;
}

.alert-context {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.context-tag {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.06);
  color: #213a4f;
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

  .alert-card {
    flex-direction: column;
    gap: 10px;
  }

  .alert-head {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
