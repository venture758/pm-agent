<script setup>
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useWorkspaceStore } from "../stores/workspace";
import ChatView from "../components/ChatView.vue";

const workspaceStore = useWorkspaceStore();
const route = useRoute();
const router = useRouter();

const chatMessages = computed(() => workspaceStore.workspace.draft?.chat_messages || []);
const workspaceId = computed(() => route.params.workspaceId || workspaceStore.workspaceId || "default");
const requirementCount = computed(() => workspaceStore.workspace.requirements.length);

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
</script>

<template>
  <section class="intake-page">
    <article class="chat-card">
      <div class="chat-header">
        <div class="chat-header-left">
          <span class="chat-status-dot" :class="{ active: workspaceStore.loading }"></span>
          <span class="chat-header-label">
            <strong>需求对话</strong>
            <small v-if="requirementCount > 0">{{ requirementCount }} 条结构化需求</small>
          </span>
        </div>
        <span class="chat-header-hint">
          {{ workspaceStore.workspace.draft?.draft_mode === "structured" ? "结构化录入" : "群消息录入" }}
        </span>
      </div>

      <ChatView
        :messages="chatMessages"
        :loading="workspaceStore.loading"
        :can-generate="requirementCount > 0"
        :generating="workspaceStore.loading"
        @send="handleSendMessage"
        @generate="generateRecommendations"
      />

      <p v-if="workspaceStore.error" class="chat-error">{{ workspaceStore.error }}</p>
    </article>
  </section>
</template>

<style scoped>
.intake-page {
  display: flex;
  justify-content: center;
  animation: pageFadeIn 0.35s ease both;
}

@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-card {
  width: min(960px, 100%);
  display: flex;
  flex-direction: column;
  min-height: calc(100vh - 200px);
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(28, 42, 56, 0.08);
  border-radius: 24px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
  overflow: hidden;
}

.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 14px 20px;
  border-bottom: 1px solid rgba(23, 32, 42, 0.06);
  background: rgba(252, 250, 245, 0.6);
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-status-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: #c6d0dc;
  transition: background 0.3s ease;
}

.chat-status-dot.active {
  background: #ba5c3d;
  box-shadow: 0 0 8px rgba(186, 92, 61, 0.4);
}

.chat-header-label {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.chat-header-label strong {
  font-size: 14px;
  font-weight: 600;
  color: #17202a;
  font-family: Georgia, "Times New Roman", serif;
}

.chat-header-label small {
  font-size: 11px;
  color: #8a9bab;
}

.chat-header-hint {
  font-size: 11px;
  color: #8a9bab;
  padding: 3px 10px;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.06);
}

.chat-card :deep(.chat-view) {
  flex: 1;
  border-radius: 0;
  background: transparent;
}

.chat-card :deep(.chat-messages-wrap) {
  padding: 18px 20px 10px;
}

.chat-card :deep(.chat-input) {
  border-top-color: rgba(23, 32, 42, 0.06);
}

.chat-card :deep(.welcome-guide) {
  padding: 56px 20px 24px;
}

.chat-card :deep(.welcome-guide h3) {
  font-size: 22px;
  font-weight: 500;
  letter-spacing: 0.01em;
  color: #17202a;
  font-family: Georgia, "Times New Roman", serif;
}

.chat-card :deep(.welcome-guide p) {
  margin: 8px 0 0;
}

.chat-error {
  padding: 8px 20px 12px;
  margin: 0;
  color: #8a1f28;
  font-size: 12px;
  font-weight: 600;
  background: rgba(138, 31, 40, 0.04);
}

@media (max-width: 860px) {
  .chat-card {
    min-height: calc(100vh - 160px);
    border-radius: 16px;
  }

  .chat-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
