<script setup>
import { computed, onMounted, watch } from "vue";
import { RouterLink, RouterView, useRoute } from "vue-router";

import { useWorkspaceStore } from "./stores/workspace";

const route = useRoute();
const workspaceStore = useWorkspaceStore();

const workspaceId = computed(() => route.params.workspaceId || "default");

const navItems = computed(() => [
  {
    label: "需求输入",
    name: "intake",
    step: "01",
    hint: "群消息、结构化需求与推荐触发",
    value: workspaceStore.workspace.requirements.length || workspaceStore.workspace.draft.requirement_rows.length,
  },
  {
    label: "业务模块",
    name: "modules",
    step: "02",
    hint: "模块负责人、B 角、熟悉度维护",
    value: workspaceStore.workspace.module_page?.total ?? workspaceStore.workspace.module_entries.length,
  },
  {
    label: "人员管理",
    name: "personnel",
    step: "03",
    hint: "角色、技能、负载、容量维护",
    value: workspaceStore.workspace.managed_members.length,
  },
  {
    label: "推荐确认",
    name: "recommendations",
    step: "04",
    hint: "推荐依据、改派、拆分与群回复预览",
    value: workspaceStore.workspace.recommendations.length,
  },
  {
    label: "平台同步",
    name: "delivery",
    step: "05",
    hint: "故事任务预览、批次同步、上传记录",
    value: workspaceStore.workspace.latest_sync_batch?.actions?.length || 0,
  },
  {
    label: "执行监控",
    name: "monitoring",
    step: "06",
    hint: "延期、阻塞、质量异常",
    value: workspaceStore.monitoring.length,
  },
  {
    label: "团队洞察",
    name: "insights",
    step: "07",
    hint: "负载热力图、单点依赖、成长建议",
    value: workspaceStore.insights.heatmap.length,
  },
]);

const currentViewLabel = computed(
  () => navItems.value.find((item) => item.name === route.name)?.label || "工作台",
);

onMounted(() => {
  workspaceStore.loadWorkspace(workspaceId.value);
});

watch(workspaceId, (nextId) => {
  workspaceStore.loadWorkspace(nextId);
});
</script>

<template>
  <div class="app-shell">
    <aside class="sidebar">
      <!-- Brand area -->
      <div class="brand-block">
        <div class="brand-icon">
          <svg viewBox="0 0 32 32" width="28" height="28" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="4" y="4" width="24" height="24" rx="4" />
            <path d="M10 16h12M16 10v12" />
          </svg>
        </div>
        <div class="brand-text">
          <p class="eyebrow">PM Agent</p>
          <h1>项目经理工作台</h1>
        </div>
      </div>

      <!-- Divider -->
      <div class="sidebar-divider"></div>

      <!-- Workspace info — inline section -->
      <section class="workspace-card">
        <div class="workspace-header">
          <div class="workspace-title">
            <span class="workspace-dot"></span>
            <h2>{{ workspaceStore.workspace.title || workspaceStore.workspace.workspace_id }}</h2>
          </div>
          <span class="soft-tag soft-tag-light">
            {{ workspaceStore.workspace.draft.draft_mode === "structured" ? "结构化" : "群消息" }}
          </span>
        </div>
        <div class="workspace-stats">
          <div class="stat-item">
            <span class="stat-num">{{ workspaceStore.workspace.knowledge_base_summary.entry_count }}</span>
            <span class="stat-label">知识库</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ workspaceStore.workspace.uploads.length }}</span>
            <span class="stat-label">上传文件</span>
          </div>
          <div class="stat-item">
            <span class="stat-num">{{ workspaceStore.workspace.updated_at ? new Date(workspaceStore.workspace.updated_at).toLocaleDateString("zh-CN") : "—" }}</span>
            <span class="stat-label">最近更新</span>
          </div>
        </div>
      </section>

      <!-- Divider -->
      <div class="sidebar-divider"></div>

      <!-- Step navigation -->
      <nav class="nav-list">
        <RouterLink
          v-for="(item, index) in navItems"
          :key="item.name"
          :to="{ name: item.name, params: { workspaceId } }"
          class="nav-link"
          :style="{ '--nav-index': index }"
        >
          <span class="nav-step">
            <span class="nav-step-dot">{{ item.step }}</span>
          </span>
          <span class="nav-copy">
            <strong>{{ item.label }}</strong>
            <small>{{ item.hint }}</small>
          </span>
          <span class="nav-value" v-if="item.value > 0">{{ item.value }}</span>
        </RouterLink>
      </nav>
    </aside>

    <main class="content">
      <RouterView />
    </main>
  </div>
</template>
