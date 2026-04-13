<script setup>
import { ElInput, ElButton } from "element-plus";
import { ref, nextTick } from "vue";

const props = defineProps({
  disabled: Boolean,
  loading: Boolean,
});

const emit = defineEmits(["send"]);

const inputText = ref("");
const inputRef = ref(null);

function handleSend() {
  const text = inputText.value.trim();
  if (!text || props.disabled || props.loading) return;
  emit("send", text);
  inputText.value = "";
}

function handleKeydown(e) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSend();
  }
}

defineExpose({ focus: () => nextTick(() => inputRef.value?.focus?.()) });
</script>

<template>
  <div class="chat-input">
    <ElInput
      ref="inputRef"
      v-model="inputText"
      type="textarea"
      :autosize="{ minRows: 1, maxRows: 4 }"
      placeholder="描述您的需求，例如：新增发票查验接口..."
      :disabled="disabled || loading"
      @keydown="handleKeydown"
      resize="none"
    />
    <ElButton
      type="primary"
      :disabled="!inputText.trim() || disabled || loading"
      :loading="loading"
      @click="handleSend"
    >
      {{ loading ? "解析中" : "发送" }}
    </ElButton>
  </div>
</template>

<style scoped>
.chat-input {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
}
.chat-input :deep(.el-textarea__inner) {
  padding: 8px 12px;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  resize: none;
}
.chat-input :deep(.el-textarea__inner):focus {
  border-color: #409eff;
}
</style>
