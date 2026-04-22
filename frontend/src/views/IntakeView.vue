<script setup>
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";

import { useWorkspaceStore } from "../stores/workspace";
import ChatView from "../components/ChatView.vue";
import PipelinePanel from "../components/PipelinePanel.vue";

const workspaceStore = useWorkspaceStore();
const route = useRoute();
const router = useRouter();

const chatMessages = computed(() => workspaceStore.workspace.draft?.chat_messages || []);
const workspaceId = computed(() => route.params.workspaceId || workspaceStore.workspaceId || "default");
const requirementCount = computed(() => workspaceStore.workspace.requirements.length);
const sessionList = computed(() => workspaceStore.session_list || []);
const activeSessionId = computed(() => workspaceStore.activeSessionId || "");
const pipelineState = computed(() => workspaceStore.pipelineState);
const pipelineActive = computed(() => workspaceStore.pipelineActive);

const sidebarCollapsed = ref(false);
const sidebarOpenMobile = ref(false);
const isNarrowScreen = ref(false);
const pipelineDrawerOpen = ref(false);
const lastHandledCompletedRunId = ref("");
const initialPipelineLoad = ref(true);

async function handleSendMessage(text) {
  try {
    await workspaceStore.sendChatMessage(text);
  } catch {
    // error already stored
  }
}

async function generateRecommendations() {
  await workspaceStore.generateRecommendations();
  await router.push({
    name: "recommendations",
    params: {
      workspaceId: workspaceId.value,
    },
  });
}

async function handleNewConversation() {
  try {
    await workspaceStore.createNewSession();
    workspaceStore.workspace.draft.chat_messages = [];
    if (isNarrowScreen.value) {
      sidebarOpenMobile.value = false;
    }
  } catch {
    // error already stored
  }
}

async function handleSwitchSession(sessionId) {
  try {
    await workspaceStore.switchSession(sessionId);
    if (isNarrowScreen.value) {
      sidebarOpenMobile.value = false;
    }
  } catch {
    // error already stored
  }
}

async function handleDeleteSession(sessionId, event) {
  event.stopPropagation();
  try {
    await workspaceStore.deleteSession(sessionId);
  } catch {
    // error already stored
  }
}

function toggleSidebar() {
  if (isNarrowScreen.value) {
    sidebarOpenMobile.value = !sidebarOpenMobile.value;
  } else {
    sidebarCollapsed.value = !sidebarCollapsed.value;
  }
}

function checkScreenSize() {
  isNarrowScreen.value = window.innerWidth < 860;
  if (!isNarrowScreen.value) {
    sidebarOpenMobile.value = false;
  }
}

async function handleStartPipeline(executionMode = "auto") {
  try {
    const result = await workspaceStore.startPipeline("", executionMode);
    if (result) {
      pipelineDrawerOpen.value = isNarrowScreen.value;
    }
  } catch {
    // error handled by store
  }
}

async function handlePipelineComplete() {
  ElMessage.success("Pipeline 分析完成，正在刷新数据");
  await workspaceStore.loadWorkspace(workspaceId.value);
}

function handlePipelineClose() {
  workspaceStore.pipelineState = null;
  workspaceStore.syncPipelinePolling();
  pipelineDrawerOpen.value = false;
}

onMounted(() => {
  checkScreenSize();
  window.addEventListener("resize", checkScreenSize);
  workspaceStore.loadSessions().catch(() => {});
  // Restore pipeline state if active
  workspaceStore.loadPipelineState().then((state) => {
    if (state && !state.is_complete) {
      if (isNarrowScreen.value) {
        pipelineDrawerOpen.value = true;
      }
    } else if (state && state.is_complete && state.run_id) {
      // Mark the already-completed run as handled so the watch doesn't
      // re-fire handlePipelineComplete() (and show the notification) on page refresh.
      lastHandledCompletedRunId.value = state.run_id;
    }
  }).catch(() => {}).finally(() => {
    initialPipelineLoad.value = false;
  });
});

watch(
  () => workspaceStore.activeSessionId,
  (newId) => {
    if (newId) {
      workspaceStore.loadSessions().catch(() => {});
    }
  },
);

watch(
  pipelineState,
  async (state) => {
    if (!state) {
      lastHandledCompletedRunId.value = "";
      return;
    }
    // During initial mount, skip the complete handler — the run already finished
    // in a previous session, so don't show a "completed" notification on refresh.
    if (initialPipelineLoad.value) return;
    if (state.is_complete && state.run_id && state.run_id !== lastHandledCompletedRunId.value) {
      lastHandledCompletedRunId.value = state.run_id;
      await handlePipelineComplete();
      return;
    }
    if (state && isNarrowScreen.value && workspaceStore.pipelineActive) {
      pipelineDrawerOpen.value = true;
    }
  },
  { deep: true },
);
</script>

<template>
  <section class="intake-page">
    <!-- Mobile overlay -->
    <div
      v-if="isNarrowScreen && sidebarOpenMobile"
      class="sidebar-overlay"
      @click="sidebarOpenMobile = false"
    ></div>

    <!-- Sidebar -->
    <aside
      class="sidebar"
      :class="{
        collapsed: !isNarrowScreen && sidebarCollapsed,
        'mobile-open': isNarrowScreen && sidebarOpenMobile,
      }"
    >
      <!-- Header: logo + collapse -->
      <div class="sidebar-header">
        <span class="sidebar-logo">PM Agent</span>
        <button class="sidebar-collapse-btn" @click="toggleSidebar" :title="sidebarCollapsed ? '展开' : '收起'">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="3" y="3" width="18" height="18" rx="3" />
            <line x1="12" y1="3" x2="12" y2="21" />
          </svg>
        </button>
      </div>

      <!-- Actions -->
      <div class="sidebar-actions">
        <button class="sidebar-action" @click="handleNewConversation">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M12 5v14M5 12h14" />
          </svg>
          <span>新对话</span>
        </button>
        <button class="sidebar-action">
          <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="7" />
            <line x1="16.5" y1="16.5" x2="21" y2="21" />
          </svg>
          <span>搜索对话</span>
        </button>
      </div>

      <!-- Recents label -->
      <div class="sidebar-section-label">最近对话</div>

      <!-- Session list -->
      <div class="sidebar-list">
        <div
          v-for="session in sessionList"
          :key="session.session_id"
          class="session-item"
          :class="{ active: session.session_id === activeSessionId }"
          @click="handleSwitchSession(session.session_id)"
        >
          <span class="session-title">{{ session.last_message_preview || "新对话" }}</span>
          <button class="session-delete-btn" @click="handleDeleteSession(session.session_id, $event)" title="删除对话">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <path d="M3 6h18M8 6V4a2 2 0 012-2h4a2 2 0 012 2v2M19 6l-1 14a2 2 0 01-2 2H8a2 2 0 01-2-2L5 6"/>
            </svg>
          </button>
        </div>
        <p v-if="!sessionList.length" class="sidebar-empty">暂无历史对话</p>
      </div>
    </aside>

    <!-- Main area -->
    <main class="main-area" :class="{ 'has-pipeline': pipelineActive && !isNarrowScreen && chatMessages.length > 0 }">
      <!-- Mobile top bar -->
      <div v-if="isNarrowScreen" class="mobile-topbar">
        <button class="hamburger" @click="toggleSidebar">
          <svg viewBox="0 0 16 16" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <path d="M2 4h12M2 8h12M2 12h12" />
          </svg>
        </button>
        <span class="mobile-model">PM Agent</span>
        <span class="mobile-spacer"></span>
      </div>

      <!-- Chat content -->
      <div class="chat-content">
        <!-- Desktop model selector -->
        <div v-if="!isNarrowScreen && chatMessages.length === 0" class="model-selector">
          <span class="model-name">PM Agent</span>
          <svg viewBox="0 0 12 8" width="12" height="8" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M2 2l4 4 4-4"/></svg>
        </div>

        <ChatView
          :messages="chatMessages"
          :loading="workspaceStore.loading"
          :can-generate="requirementCount > 0"
          :generating="workspaceStore.loading"
          @send="handleSendMessage"
          @generate="generateRecommendations"
          @start-pipeline="handleStartPipeline"
        />

        <!-- Action chips (when no messages) -->
        <div v-if="chatMessages.length === 0" class="action-chips">
          <span class="action-chip">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="8" cy="6" r="4"/>
              <path d="M4 14c0-2.2 1.8-4 4-4s4 1.8 4 4"/>
            </svg>
            团队知识库
          </span>
        </div>

        <p v-if="workspaceStore.error" class="chat-error">{{ workspaceStore.error }}</p>
      </div>
    </main>

    <!-- Desktop Pipeline Panel -->
    <aside
      v-if="pipelineActive && !isNarrowScreen && pipelineState && chatMessages.length > 0"
      class="pipeline-right-panel"
    >
      <PipelinePanel
        :pipeline-state="pipelineState"
        @close="handlePipelineClose"
        @complete="handlePipelineComplete"
      />
    </aside>

    <!-- Mobile Pipeline Drawer -->
    <div
      v-if="isNarrowScreen && pipelineDrawerOpen && pipelineState"
      class="pipeline-drawer-overlay"
      @click="pipelineDrawerOpen = false"
    >
      <div class="pipeline-drawer" @click.stop>
        <PipelinePanel
          :pipeline-state="pipelineState"
          @close="handlePipelineClose"
          @complete="handlePipelineComplete"
        />
      </div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Source+Sans+3:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;600&display=swap');

.intake-page {
  display: flex;
  height: 100vh;
  animation: pageFadeIn 0.35s ease both;
  position: relative;
  overflow: hidden;
  font-family: 'Source Sans 3', 'Noto Sans SC', -apple-system, sans-serif;
}

@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ====== Sidebar ====== */
.sidebar {
  width: 260px;
  min-width: 260px;
  background: #f9f9f9;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease, min-width 0.2s ease;
  position: relative;
  overflow: hidden;
  border-right: 1px solid #e5e5e5;
}

.sidebar.collapsed {
  width: 60px;
  min-width: 60px;
}

.sidebar.collapsed .sidebar-logo,
.sidebar.collapsed .sidebar-action span,
.sidebar.collapsed .sidebar-section-label,
.sidebar.collapsed .session-title,
.sidebar.collapsed .sidebar-empty {
  display: none;
}

.sidebar.collapsed .sidebar-header {
  justify-content: center;
  padding: 12px 8px;
}

.sidebar.collapsed .sidebar-actions {
  padding: 4px 8px;
}

.sidebar.collapsed .sidebar-action {
  justify-content: center;
  padding: 8px;
}

/* Mobile sidebar */
@media (max-width: 860px) {
  .sidebar {
    position: fixed;
    top: 0;
    left: 0;
    bottom: 0;
    width: 280px;
    min-width: 280px;
    z-index: 200;
    transform: translateX(-100%);
    transition: transform 0.25s ease;
    box-shadow: 4px 0 24px rgba(0, 0, 0, 0.08);
  }
  .sidebar.mobile-open {
    transform: translateX(0);
  }
}

.sidebar-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.2);
  z-index: 199;
}

/* Sidebar header */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  flex-shrink: 0;
}

.sidebar-logo {
  font-size: 15px;
  font-weight: 600;
  color: #111;
  letter-spacing: -0.01em;
}

.sidebar-collapse-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #888;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.sidebar-collapse-btn:hover {
  background: rgba(0, 0, 0, 0.06);
  color: #333;
}

/* Sidebar actions (New chat, Search) */
.sidebar-actions {
  padding: 4px 8px;
  display: flex;
  flex-direction: column;
  gap: 1px;
  flex-shrink: 0;
}

.sidebar-action {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #333;
  font-family: 'Source Sans 3', 'Noto Sans SC', sans-serif;
  font-size: 14px;
  font-weight: 400;
  cursor: pointer;
  transition: background 0.12s ease;
  text-align: left;
  width: 100%;
}

.sidebar-action:hover {
  background: rgba(0, 0, 0, 0.05);
}

.sidebar-action svg {
  flex-shrink: 0;
}

/* Section label */
.sidebar-section-label {
  font-size: 12px;
  font-weight: 500;
  color: #999;
  padding: 16px 14px 6px;
  flex-shrink: 0;
}

/* Session list */
.sidebar-list {
  flex: 1;
  overflow-y: auto;
  padding: 2px 8px 8px;
}

.sidebar-list::-webkit-scrollbar {
  width: 4px;
}

.sidebar-list::-webkit-scrollbar-thumb {
  background: #d4d4d4;
  border-radius: 2px;
}

.session-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 7px 10px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.12s ease;
  color: #444;
  font-size: 14px;
  gap: 8px;
}

.session-item:hover {
  background: rgba(0, 0, 0, 0.05);
}

.session-item.active {
  background: rgba(0, 0, 0, 0.07);
  color: #111;
}

.session-title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.session-delete-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #999;
  cursor: pointer;
  padding: 2px;
  border-radius: 4px;
  opacity: 0;
  transition: opacity 0.12s ease, color 0.12s ease, background 0.12s ease;
  flex-shrink: 0;
}

.session-item:hover .session-delete-btn {
  opacity: 1;
}

.session-delete-btn:hover {
  color: #c0392b;
  background: rgba(0, 0, 0, 0.06);
}

.sidebar-empty {
  text-align: center;
  padding: 24px 16px;
  color: #bbb;
  font-size: 13px;
}

/* ====== Main area ====== */
.main-area {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #fff;
  min-width: 0;
}

/* Mobile top bar */
.mobile-topbar {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  background: #fff;
  border-bottom: 1px solid #eee;
  flex-shrink: 0;
}

.hamburger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #333;
  cursor: pointer;
  padding: 4px;
  border-radius: 6px;
}

.hamburger:hover {
  background: #f0f0f0;
}

.mobile-model {
  flex: 1;
  text-align: center;
  font-size: 15px;
  font-weight: 600;
  color: #111;
}

.mobile-spacer {
  width: 26px;
}

/* Chat content area */
.chat-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  max-width: 760px;
  width: 100%;
  margin: 0 auto;
}

.main-area.has-pipeline .chat-content {
  max-width: 600px;
}

/* Desktop right pipeline panel */
.pipeline-right-panel {
  width: 420px;
  min-width: 420px;
  border-left: 1px solid #e5e5e5;
  background: #fafafa;
  display: flex;
  flex-direction: column;
}

/* Mobile pipeline drawer */
.pipeline-drawer-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  z-index: 300;
  display: flex;
  align-items: flex-end;
}

.pipeline-drawer {
  width: 100%;
  height: 85vh;
  background: #fafafa;
  border-radius: 12px 12px 0 0;
  animation: drawerSlideUp 0.3s ease both;
}

@keyframes drawerSlideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}

/* Model selector */
.model-selector {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 6px 14px;
  margin: 12px auto 0;
  border-radius: 10px;
  border: 1px solid #eee;
  background: #fff;
  color: #111;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  flex-shrink: 0;
}

.model-selector:hover {
  background: #f7f7f7;
}

/* Action chips */
.action-chips {
  display: flex;
  justify-content: center;
  padding: 16px 20px 8px;
  flex-shrink: 0;
}

.action-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid #e0e0e0;
  background: #fff;
  color: #444;
  font-size: 13px;
  font-weight: 500;
  cursor: default;
  transition: all 0.15s ease;
}

.action-chip:hover {
  background: #f7f7f7;
  border-color: #ccc;
}

/* Chat error */
.chat-error {
  padding: 8px 20px 12px;
  margin: 0;
  color: #a54b30;
  font-size: 12px;
  font-weight: 600;
  background: rgba(186, 92, 61, 0.04);
  border-radius: 8px;
  margin: 0 16px 8px;
}

/* Override ChatView deep styles for ChatGPT aesthetic */
.chat-content :deep(.chat-view) {
  flex: 1;
  border-radius: 0;
  background: transparent;
  border: none;
  display: flex;
  flex-direction: column;
}

.chat-content :deep(.welcome-guide) {
  text-align: center;
  padding: 80px 24px 40px;
}

.chat-content :deep(.welcome-guide h3) {
  font-size: 28px;
  font-weight: 500;
  color: #111;
  font-family: 'Noto Sans SC', 'Source Sans 3', sans-serif;
  letter-spacing: -0.01em;
  margin: 0 0 8px;
}

.chat-content :deep(.welcome-guide .muted) {
  color: #888;
  font-size: 14px;
  margin: 0;
}

.chat-content :deep(.chat-messages-wrap) {
  padding: 8px 16px;
}

.chat-content :deep(.chat-input) {
  border-top: none;
  background: transparent;
  padding: 12px 8px 16px;
}

.chat-content :deep(.el-textarea__inner) {
  border: 1px solid #e0e0e0 !important;
  border-radius: 16px !important;
  padding: 12px 18px !important;
  font-size: 14px !important;
  font-family: 'Source Sans 3', 'Noto Sans SC', sans-serif !important;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04) !important;
  transition: box-shadow 0.2s ease, border-color 0.2s ease !important;
}

.chat-content :deep(.el-textarea__inner):focus {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08) !important;
  border-color: #bbb !important;
}

.chat-content :deep(.el-button) {
  border-radius: 12px !important;
}

@media (max-width: 860px) {
  .intake-page {
    height: 100vh;
  }

  .chat-content {
    max-width: 100%;
  }

  .model-selector {
    display: none;
  }

  .action-chips {
    padding: 8px 16px;
  }

  .chat-content :deep(.welcome-guide) {
    padding: 60px 20px 32px;
  }

  .chat-content :deep(.welcome-guide h3) {
    font-size: 24px;
  }
}
</style>
