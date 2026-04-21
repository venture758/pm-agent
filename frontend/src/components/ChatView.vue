<script setup>
import { ElScrollbar } from "element-plus";
import { ref, nextTick, watch, computed } from "vue";
import ChatInput from "./ChatInput.vue";
import ChatMessageBubble from "./ChatMessageBubble.vue";

const props = defineProps({
  messages: {
    type: Array,
    default: () => [],
  },
  loading: {
    type: Boolean,
    default: false,
  },
  canGenerate: {
    type: Boolean,
    default: false,
  },
  generating: {
    type: Boolean,
    default: false,
  },
});

const emit = defineEmits(["send", "generate", "start-pipeline"]);

const scrollbarRef = ref(null);
const showWelcome = ref(props.messages.length === 0);
const lastActionableAssistantIndex = computed(() => {
  for (let index = props.messages.length - 1; index >= 0; index -= 1) {
    const message = props.messages[index];
    if (message?.role !== "assistant") {
      continue;
    }
    if (Array.isArray(message.parsed_requirements) && message.parsed_requirements.length) {
      return index;
    }
  }
  return -1;
});

async function handleSend(text) {
  showWelcome.value = false;
  emit("send", text);
  await nextTick();
  scrollToBottom();
}

function scrollToBottom() {
  nextTick(() => {
    const wrap = scrollbarRef.value?.wrapRef;
    if (wrap) {
      wrap.scrollTop = wrap.scrollHeight;
    }
  });
}

watch(
  () => props.messages,
  () => scrollToBottom(),
  { deep: true }
);
</script>

<template>
  <div class="chat-view">
    <div v-if="showWelcome" class="welcome-guide">
      <h3>请直接输入需求</h3>
      <p class="muted">支持粘贴群消息原文，回车发送，Shift + Enter 换行。</p>
    </div>

    <ElScrollbar ref="scrollbarRef" class="chat-messages" wrap-class="chat-messages-wrap">
      <div class="messages-container">
        <ChatMessageBubble
          v-for="(msg, index) in messages"
          :key="index"
          :message="msg"
          :is-user="msg.role === 'user'"
          :show-generate-action="index === lastActionableAssistantIndex"
          :can-generate="canGenerate"
          :generating="generating"
          @generate="emit('generate')"
          @start-pipeline="(mode) => emit('start-pipeline', mode)"
        />
        <div v-if="loading" class="message-bubble is-assistant">
          <div class="bubble-content is-assistant">
            <span class="thinking">正在解析需求<span class="dots">...</span></span>
          </div>
        </div>
      </div>
    </ElScrollbar>

    <ChatInput :loading="loading" @send="handleSend" />
  </div>
</template>

<style scoped>
.chat-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
  border-radius: 0;
  overflow: hidden;
}
.welcome-guide {
  padding: 28px 24px;
  text-align: center;
  color: #495c6d;
}
.welcome-guide h3 {
  margin: 0;
  color: #2b3f51;
  font-size: 22px;
  font-weight: 500;
}
.welcome-guide .muted {
  color: #6c7f90;
  font-size: 13px;
}
.chat-messages {
  flex: 1;
  min-height: 0;
}
.chat-messages-wrap {
  padding: 16px;
}
.messages-container {
  display: flex;
  flex-direction: column;
}
.thinking {
  color: #909399;
}
.dots {
  animation: dots 1.5s infinite;
}
@keyframes dots {
  0%, 20% { opacity: 0; }
  40% { opacity: 1; }
  60% { opacity: 0; }
  80% { opacity: 1; }
  100% { opacity: 0; }
}
</style>
