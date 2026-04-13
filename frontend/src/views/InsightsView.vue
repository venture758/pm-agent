<script setup>
import { computed, onMounted, ref } from "vue";

import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();

const memberFilter = ref("");
const levelFilter = ref("all");
const showCompare = ref(false);

const levelOptions = [
  { value: "all", label: "全部" },
  { value: "高", label: "高负载" },
  { value: "中", label: "中负载" },
  { value: "低", label: "低负载" },
];

onMounted(() => {
  workspaceStore.refreshInsights();
});

function utilizationPercent(entry) {
  return Math.max(0, Math.min(100, Math.round((Number(entry.utilization) || 0) * 100)));
}

function healthColor(score) {
  if (score >= 80) return "#3a8a5c";
  if (score >= 60) return "#ba8c3d";
  return "#8a1f28";
}

function healthLabel(score) {
  if (score >= 80) return "健康";
  if (score >= 60) return "一般";
  if (score >= 40) return "预警";
  return "高危";
}

function trendArrow(current, previous, lowerIsBetter = false) {
  if (previous == null) return { icon: "—", color: "#8a9bab" };
  if (current === previous) return { icon: "→", color: "#8a9bab" };
  const improved = lowerIsBetter ? current < previous : current > previous;
  return improved
    ? { icon: "\u2191", color: "#3a8a5c" }
    : { icon: "\u2193", color: "#8a1f28" };
}

function formatTime(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getMonth() + 1}/${d.getDate()} ${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

const previousSummary = computed(() => {
  if (workspaceStore.insightHistory.length < 2) return null;
  return workspaceStore.insightHistory[1].summary;
});

const filteredHeatmap = computed(() => {
  let data = workspaceStore.insights.heatmap || [];
  if (memberFilter.value.trim()) {
    const q = memberFilter.value.trim().toLowerCase();
    data = data.filter((e) => e.member.toLowerCase().includes(q));
  }
  if (levelFilter.value !== "all") {
    data = data.filter((e) => e.level === levelFilter.value);
  }
  return data;
});

const filteredSinglePoints = computed(() => {
  let data = workspaceStore.insights.single_points || [];
  if (memberFilter.value.trim()) {
    const q = memberFilter.value.trim().toLowerCase();
    data = data.filter((e) => e.member.toLowerCase().includes(q));
  }
  return data;
});

const filteredGrowth = computed(() => {
  let data = workspaceStore.insights.growth_suggestions || [];
  if (memberFilter.value.trim()) {
    const q = memberFilter.value.trim().toLowerCase();
    data = data.filter((e) => e.member.toLowerCase().includes(q));
  }
  return data;
});

function utilizationBarColor(level) {
  switch (level) {
    case "高":
      return "linear-gradient(90deg, #ba5c3d 0%, #8a1f28 100%)";
    case "中":
      return "linear-gradient(90deg, #ba8c3d 0%, #ba5c3d 100%)";
    default:
      return "linear-gradient(90deg, #3a8a5c 0%, #ba8c3d 100%)";
  }
}

async function comparePrevious() {
  showCompare.value = !showCompare.value;
  if (showCompare.value && workspaceStore.insightHistory.length < 2) {
    await workspaceStore.loadInsightHistory();
  }
}

function healthRingPath(score) {
  const r = 52;
  const circumference = 2 * Math.PI * r;
  const offset = circumference - (score / 100) * circumference;
  return `stroke-dasharray: ${circumference}; stroke-dashoffset: ${offset};`;
}
</script>

<template>
  <section class="page-grid insights-layout">
    <!-- Top summary bar -->
    <article class="panel panel-highlight summary-bar">
      <div class="summary-head">
        <div>
          <p class="section-kicker">Insight</p>
          <h2 class="panel-title">团队洞察</h2>
          <p class="summary-time" v-if="workspaceStore.insightHistory.length">
            最近刷新：{{ formatTime(workspaceStore.insightHistory[0]?.snapshot_at) }}
          </p>
        </div>
        <div class="summary-actions">
          <button class="ghost-button" :class="{ active: showCompare }" @click="comparePrevious">
            {{ showCompare ? "收起对比" : "对比上次" }}
          </button>
          <button class="secondary-button" :disabled="workspaceStore.loading" @click="workspaceStore.refreshInsights()">
            刷新洞察
          </button>
        </div>
      </div>

      <!-- Metric cards -->
      <div class="metric-row" v-if="workspaceStore.insightSummary">
        <div class="metric-card metric-health">
          <div class="health-ring">
            <svg viewBox="0 0 120 120" width="88" height="88">
              <circle cx="60" cy="60" r="52" fill="none" stroke="#e6edf5" stroke-width="8" />
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                :stroke="healthColor(workspaceStore.insightSummary.team_health_score)"
                stroke-width="8"
                stroke-linecap="round"
                :style="healthRingPath(workspaceStore.insightSummary.team_health_score)"
                transform="rotate(-90 60 60)"
              />
            </svg>
            <span class="health-value">{{ workspaceStore.insightSummary.team_health_score }}</span>
          </div>
          <span class="metric-label">团队健康</span>
          <span class="metric-sub">{{ healthLabel(workspaceStore.insightSummary.team_health_score) }}</span>
          <span
            v-if="previousSummary"
            class="metric-trend"
            :style="{ color: trendArrow(workspaceStore.insightSummary.team_health_score, previousSummary.team_health_score).color }"
          >
            {{ trendArrow(workspaceStore.insightSummary.team_health_score, previousSummary.team_health_score).icon }}
          </span>
        </div>

        <div class="metric-card" v-if="workspaceStore.insightSummary.high_load_count > 0">
          <span class="metric-big" style="color: #8a1f28">{{ workspaceStore.insightSummary.high_load_count }}</span>
          <span class="metric-label">超载</span>
          <span
            v-if="previousSummary"
            class="metric-trend"
            :style="{ color: trendArrow(workspaceStore.insightSummary.high_load_count, previousSummary.high_load_count, true).color }"
          >
            {{ trendArrow(workspaceStore.insightSummary.high_load_count, previousSummary.high_load_count, true).icon }}
          </span>
        </div>
        <div class="metric-card" v-else>
          <span class="metric-big" style="color: #3a8a5c">0</span>
          <span class="metric-label">超载</span>
        </div>

        <div class="metric-card">
          <span class="metric-big">{{ workspaceStore.insightSummary.single_point_risk_count }}</span>
          <span class="metric-label">单点风险</span>
          <span
            v-if="previousSummary"
            class="metric-trend"
            :style="{ color: trendArrow(workspaceStore.insightSummary.single_point_risk_count, previousSummary.single_point_risk_count, true).color }"
          >
            {{ trendArrow(workspaceStore.insightSummary.single_point_risk_count, previousSummary.single_point_risk_count, true).icon }}
          </span>
        </div>

        <div class="metric-card">
          <span class="metric-big">{{ workspaceStore.insightSummary.growth_opportunity_count }}</span>
          <span class="metric-label">成长机会</span>
        </div>
      </div>
    </article>

    <!-- Comparison panel -->
    <article v-if="showCompare && previousSummary" class="panel panel-wide compare-panel">
      <div class="panel-header">
        <h2 class="panel-title" style="font-size: 20px">对比变化</h2>
      </div>
      <div class="compare-grid">
        <div class="compare-item">
          <span class="compare-label">健康分</span>
          <span class="compare-values">
            <span class="compare-prev">{{ previousSummary.team_health_score }}</span>
            <span class="compare-arrow">→</span>
            <span class="compare-curr" :style="{ color: healthColor(workspaceStore.insightSummary.team_health_score) }">
              {{ workspaceStore.insightSummary.team_health_score }}
            </span>
          </span>
        </div>
        <div class="compare-item">
          <span class="compare-label">平均利用率</span>
          <span class="compare-values">
            <span class="compare-prev">{{ Math.round(previousSummary.avg_utilization * 100) }}%</span>
            <span class="compare-arrow">→</span>
            <span class="compare-curr">{{ Math.round(workspaceStore.insightSummary.avg_utilization * 100) }}%</span>
          </span>
        </div>
        <div class="compare-item">
          <span class="compare-label">单点风险</span>
          <span class="compare-values">
            <span class="compare-prev">{{ previousSummary.single_point_risk_count }}</span>
            <span class="compare-arrow">→</span>
            <span class="compare-curr">{{ workspaceStore.insightSummary.single_point_risk_count }}</span>
          </span>
        </div>
        <div class="compare-item">
          <span class="compare-label">团队人数</span>
          <span class="compare-values">
            <span class="compare-prev">{{ previousSummary.member_count }}</span>
            <span class="compare-arrow">→</span>
            <span class="compare-curr">{{ workspaceStore.insightSummary.member_count }}</span>
          </span>
        </div>
      </div>
    </article>

    <!-- Toolbar -->
    <article class="panel panel-wide toolbar-panel">
      <div class="insight-toolbar">
        <input
          class="search-input"
          type="text"
          placeholder="搜索成员…"
          v-model="memberFilter"
        />
        <div class="chip-group">
          <button
            v-for="opt in levelOptions"
            :key="opt.value"
            class="toggle-chip"
            :class="{ active: levelFilter === opt.value }"
            @click="levelFilter = opt.value"
          >
            {{ opt.label }}
          </button>
        </div>
      </div>
    </article>

    <!-- Heatmap -->
    <article class="panel">
      <div class="panel-header">
        <div>
          <p class="section-kicker">Load</p>
          <h2 class="panel-title" style="font-size: 22px">成员负载</h2>
        </div>
        <span class="panel-count">{{ filteredHeatmap.length }} / {{ workspaceStore.insights.heatmap.length }}</span>
      </div>
      <div v-if="filteredHeatmap.length" class="stack-list">
        <div v-for="entry in filteredHeatmap" :key="entry.member" class="mini-card heatmap-card">
          <div class="title-row">
            <h3>{{ entry.member }}</h3>
            <span
              class="soft-tag"
              :class="entry.level === '高' ? 'soft-tag-danger' : entry.level === '中' ? 'soft-tag-warm' : 'soft-tag-light'"
            >{{ entry.level }}</span>
          </div>
          <div class="utilization-row">
            <span class="util-label">负载 {{ entry.load }} / 容量 {{ entry.capacity }}</span>
            <span class="util-pct">{{ utilizationPercent(entry) }}%</span>
          </div>
          <div class="progress-track">
            <div class="progress-fill" :style="{ width: `${utilizationPercent(entry)}%`, background: utilizationBarColor(entry.level) }"></div>
          </div>
        </div>
      </div>
      <p v-else class="muted">暂无负载数据。</p>
    </article>

    <!-- Single points -->
    <article class="panel">
      <div class="panel-header">
        <div>
          <p class="section-kicker">Risk</p>
          <h2 class="panel-title" style="font-size: 22px">单点依赖</h2>
        </div>
        <span class="panel-count">{{ filteredSinglePoints.length }}</span>
      </div>
      <div v-if="filteredSinglePoints.length" class="stack-list">
        <div
          v-for="risk in filteredSinglePoints"
          :key="`${risk.member}-${risk.module_key}`"
          class="mini-card risk-card"
        >
          <div class="title-row">
            <div class="risk-left">
              <span class="risk-dot"></span>
              <h3>{{ risk.member }}</h3>
            </div>
            <span class="pill-item">{{ risk.module_key }}</span>
          </div>
          <p>{{ risk.reason }}</p>
          <p class="muted" v-if="risk.related_requirements?.length">
            相关需求：{{ risk.related_requirements.join(", ") }}
          </p>
        </div>
      </div>
      <p v-else class="muted">暂无单点依赖。</p>
    </article>

    <!-- Growth suggestions -->
    <article class="panel panel-wide">
      <div class="panel-header">
        <div>
          <p class="section-kicker">Growth</p>
          <h2 class="panel-title" style="font-size: 22px">成长建议</h2>
        </div>
        <span class="panel-count">{{ filteredGrowth.length }}</span>
      </div>
      <div v-if="filteredGrowth.length" class="kanban-grid">
        <div
          v-for="suggestion in filteredGrowth"
          :key="`${suggestion.member}-${suggestion.module_key}`"
          class="mini-card growth-card"
        >
          <div class="title-row">
            <h3>{{ suggestion.member }}</h3>
            <span class="pill-item">{{ suggestion.module_key }}</span>
          </div>
          <p>{{ suggestion.suggestion }}</p>
          <p class="muted">{{ suggestion.rationale }}</p>
        </div>
      </div>
      <p v-else class="muted">暂无成长建议。</p>
    </article>
  </section>
</template>
