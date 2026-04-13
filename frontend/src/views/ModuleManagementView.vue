<script setup>
import { computed, onMounted, ref, watch } from "vue";

import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();

const moduleForms = ref([]);
const newModule = ref(createModuleForm());
const showCreateModal = ref(false);
const modulePage = computed(() => workspaceStore.workspace.module_page || { page: 1, page_size: 50, total: 0, total_pages: 1, filters: {} });
const queryForm = ref({
  big_module: "",
  function_module: "",
  primary_owner: "",
});
const groupedModuleForms = computed(() => {
  const groups = [];
  moduleForms.value.forEach((form) => {
    const lastGroup = groups[groups.length - 1];
    if (lastGroup && lastGroup.big_module === form.big_module) {
      lastGroup.rows.push(form);
      return;
    }
    groups.push({
      big_module: form.big_module,
      rows: [form],
    });
  });
  return groups;
});

function createModuleForm(entry = {}) {
  return {
    original_key: entry.key || "",
    big_module: entry.big_module || "",
    function_module: entry.function_module || "",
    primary_owner: entry.primary_owner || "",
    backup_owners_text: formatNames(entry.backup_owners || (entry.backup_owner ? [entry.backup_owner] : [])),
    familiar_members: resolveMembersByLevel(entry, "熟悉"),
    aware_members: resolveMembersByLevel(entry, "了解"),
    unfamiliar_members: resolveMembersByLevel(entry, "不了解"),
  };
}

function formatNames(values) {
  return (Array.isArray(values) ? values : [])
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .join(", ");
}

function parseNames(text) {
  const names = [];
  String(text || "")
    .split(/[\n,，]+/)
    .map((item) => item.trim())
    .filter(Boolean)
    .forEach((name) => {
      if (!names.includes(name)) {
        names.push(name);
      }
    });
  return names;
}

function resolveMembersByLevel(entry, targetLevel) {
  if (targetLevel === "熟悉" && Array.isArray(entry.familiar_members)) {
    return formatNames(entry.familiar_members);
  }
  if (targetLevel === "了解" && Array.isArray(entry.aware_members)) {
    return formatNames(entry.aware_members);
  }
  if (targetLevel === "不了解" && Array.isArray(entry.unfamiliar_members)) {
    return formatNames(entry.unfamiliar_members);
  }
  return formatMembersByLevel(entry.familiarity_by_member || {}, targetLevel);
}

function formatMembersByLevel(map, targetLevel) {
  return Object.entries(map)
    .filter(([, level]) => {
      const normalizedLevel = level === "一般" ? "了解" : level;
      return normalizedLevel === targetLevel;
    })
    .map(([member]) => member)
    .join(", ");
}

function modulePayload(form) {
  return {
    big_module: form.big_module,
    function_module: form.function_module,
    primary_owner: form.primary_owner,
    backup_owners: parseNames(form.backup_owners_text),
    familiar_members: parseNames(form.familiar_members),
    aware_members: parseNames(form.aware_members),
    unfamiliar_members: parseNames(form.unfamiliar_members),
  };
}

function notifyActionResult(success, message) {
  const prefix = success ? "处理成功" : "处理失败";
  const detail = String(message || "").trim();
  const content = detail ? `${prefix}：${detail}` : prefix;
  try {
    window.alert(content);
  } catch (_error) {
    // no-op for non-browser test/runtime environments
  }
}

watch(
  () => workspaceStore.workspace.module_entries,
  (entries) => {
    moduleForms.value = (entries || []).map((entry) => createModuleForm(entry));
  },
  { immediate: true, deep: true },
);

watch(
  () => modulePage.value.filters,
  (filters) => {
    queryForm.value = {
      big_module: String(filters?.big_module || ""),
      function_module: String(filters?.function_module || ""),
      primary_owner: String(filters?.primary_owner || ""),
    };
  },
  { immediate: true, deep: true },
);

onMounted(() => {
  workspaceStore.refreshModules({
    page: 1,
    page_size: 50,
  });
});

function openCreateModal() {
  newModule.value = createModuleForm();
  showCreateModal.value = true;
}

function closeCreateModal() {
  newModule.value = createModuleForm();
  showCreateModal.value = false;
}

async function createManagedModule() {
  try {
    await workspaceStore.createModule(modulePayload(newModule.value));
    notifyActionResult(true, workspaceStore.workspace.messages?.[0] || "已新增业务模块");
    closeCreateModal();
  } catch (error) {
    notifyActionResult(false, error instanceof Error ? error.message : "新增业务模块失败");
  }
}

async function saveManagedModule(form) {
  try {
    await workspaceStore.updateModule(form.original_key, {
      ...modulePayload(form),
      original_key: form.original_key,
    });
    notifyActionResult(true, workspaceStore.workspace.messages?.[0] || "已保存业务模块");
  } catch (error) {
    notifyActionResult(false, error instanceof Error ? error.message : "保存业务模块失败");
  }
}

async function deleteManagedModule(form) {
  await workspaceStore.deleteModule(form.original_key);
}

async function applySearch() {
  await workspaceStore.refreshModules({
    page: 1,
    page_size: modulePage.value.page_size || 50,
    big_module: queryForm.value.big_module,
    function_module: queryForm.value.function_module,
    primary_owner: queryForm.value.primary_owner,
  });
}

async function resetSearch() {
  queryForm.value = {
    big_module: "",
    function_module: "",
    primary_owner: "",
  };
  await workspaceStore.refreshModules({
    page: 1,
    page_size: 50,
    ...queryForm.value,
  });
}

async function changePage(page) {
  if (page < 1 || page > modulePage.value.total_pages || page === modulePage.value.page) {
    return;
  }
  await workspaceStore.refreshModules({
    ...workspaceStore.moduleQuery,
    page,
  });
}
</script>

<template>
  <section class="module-page">
    <!-- Header card -->
    <article class="card module-header-card">
      <div class="module-header-row">
        <div>
          <p class="section-kicker">Modules</p>
          <h2 class="panel-title" style="font-size: 24px">业务模块维护</h2>
        </div>
        <div class="module-header-actions">
          <span class="module-stat-tag">{{ modulePage.total }} 条</span>
          <button class="accent-button" :disabled="workspaceStore.loading" @click="openCreateModal">
            <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <line x1="8" y1="3" x2="8" y2="13" />
              <line x1="3" y1="8" x2="13" y2="8" />
            </svg>
            新增
          </button>
        </div>
      </div>
      <p class="muted" style="margin-top: 8px">支持维护模块负责人、B 角和成员熟悉度，也可通过 Excel 批量导入。</p>
      <p v-if="workspaceStore.error" class="error-text" style="margin-top: 8px">{{ workspaceStore.error }}</p>
    </article>

    <!-- Search + Table card -->
    <article class="card table-card">
      <!-- Search bar -->
      <div class="search-bar">
        <div class="search-fields">
          <label class="search-field">
            <span>大模块</span>
            <input v-model="queryForm.big_module" placeholder="模糊匹配" />
          </label>
          <label class="search-field">
            <span>功能模块</span>
            <input v-model="queryForm.function_module" placeholder="模糊匹配" />
          </label>
          <label class="search-field">
            <span>负责人</span>
            <input v-model="queryForm.primary_owner" placeholder="模糊匹配" />
          </label>
        </div>
        <div class="search-actions">
          <button class="search-button" :disabled="workspaceStore.loading" @click="applySearch">查询</button>
          <button class="reset-button" :disabled="workspaceStore.loading" @click="resetSearch">重置</button>
        </div>
      </div>

      <!-- Data table -->
      <div v-if="moduleForms.length" class="module-table-wrap">
        <table class="module-table">
          <thead>
            <tr>
              <th rowspan="2">大模块</th>
              <th rowspan="2">功能模块</th>
              <th rowspan="2">负责人</th>
              <th rowspan="2">B 角</th>
              <th colspan="3">熟悉度</th>
              <th rowspan="2">操作</th>
            </tr>
            <tr>
              <th>熟悉</th>
              <th>了解</th>
              <th>不了解</th>
            </tr>
          </thead>
          <tbody>
            <template v-for="group in groupedModuleForms" :key="group.big_module || 'ungrouped'">
              <tr v-for="(form, index) in group.rows" :key="form.original_key">
                <td v-if="index === 0" :rowspan="group.rows.length" class="module-cell-merged">
                  <input v-model="form.big_module" class="table-input" />
                </td>
                <td><input v-model="form.function_module" class="table-input" /></td>
                <td><input v-model="form.primary_owner" class="table-input" /></td>
                <td><input v-model="form.backup_owners_text" class="table-input" /></td>
                <td><textarea v-model="form.familiar_members" rows="2" class="table-textarea" placeholder="逗号分隔" /></td>
                <td><textarea v-model="form.aware_members" rows="2" class="table-textarea" placeholder="逗号分隔" /></td>
                <td><textarea v-model="form.unfamiliar_members" rows="2" class="table-textarea" placeholder="逗号分隔" /></td>
                <td class="module-cell-actions">
                  <button class="save-button" :disabled="workspaceStore.loading" @click="saveManagedModule(form)">保存</button>
                  <button class="delete-button" :disabled="workspaceStore.loading" @click="deleteManagedModule(form)">删除</button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state">
        <svg viewBox="0 0 48 48" width="36" height="36" fill="none" stroke="#8a9bab" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
          <rect x="8" y="6" width="32" height="36" rx="4" />
          <path d="M16 18h16M16 26h12M16 34h8" />
        </svg>
        <p>还没有维护业务模块，点击右上方新增或上传 Excel。</p>
      </div>

      <!-- Pagination -->
      <div v-if="moduleForms.length" class="pagination-bar">
        <button
          class="page-button"
          :disabled="workspaceStore.loading || modulePage.page <= 1"
          @click="changePage(modulePage.page - 1)"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="10 3 5 8 10 13" />
          </svg>
        </button>
        <span class="page-label">
          第 <strong>{{ modulePage.page }}</strong> / {{ modulePage.total_pages }} 页
        </span>
        <button
          class="page-button"
          :disabled="workspaceStore.loading || modulePage.page >= modulePage.total_pages"
          @click="changePage(modulePage.page + 1)"
        >
          <svg viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="6 3 11 8 6 13" />
          </svg>
        </button>
      </div>
    </article>

    <!-- Create modal -->
    <div v-if="showCreateModal" class="modal-backdrop" @click.self="closeCreateModal">
      <section class="card modal-card">
        <div class="modal-head">
          <div>
            <p class="section-kicker">New Module</p>
            <h2 class="panel-title" style="font-size: 20px">新增业务模块</h2>
          </div>
          <button class="close-button" @click="closeCreateModal">
            <svg viewBox="0 0 16 16" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <line x1="4" y1="4" x2="12" y2="12" />
              <line x1="12" y1="4" x2="4" y2="12" />
            </svg>
          </button>
        </div>
        <div class="modal-form">
          <label class="form-field">
            <span>大模块</span>
            <input v-model="newModule.big_module" placeholder="例如：税务" />
          </label>
          <label class="form-field">
            <span>功能模块</span>
            <input v-model="newModule.function_module" placeholder="例如：发票接口" />
          </label>
          <label class="form-field">
            <span>主要负责人</span>
            <input v-model="newModule.primary_owner" placeholder="人员管理中已维护的姓名" />
          </label>
          <label class="form-field">
            <span>B 角（多人逗号分隔）</span>
            <input v-model="newModule.backup_owners_text" placeholder="可选" />
          </label>
          <label class="form-field form-field--wide">
            <span>熟悉成员</span>
            <textarea v-model="newModule.familiar_members" rows="2" placeholder="逗号分隔" />
          </label>
          <label class="form-field form-field--wide">
            <span>了解成员</span>
            <textarea v-model="newModule.aware_members" rows="2" placeholder="逗号分隔" />
          </label>
          <label class="form-field form-field--wide">
            <span>不了解成员</span>
            <textarea v-model="newModule.unfamiliar_members" rows="2" placeholder="逗号分隔" />
          </label>
        </div>
        <div class="modal-footer">
          <button class="accent-button" :disabled="workspaceStore.loading" @click="createManagedModule">保存</button>
          <button class="close-button" :disabled="workspaceStore.loading" @click="closeCreateModal">取消</button>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.module-page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  animation: pageFadeIn 0.35s ease both;
}

@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.card {
  background: rgba(255, 255, 255, 0.92);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 22px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
}

/* Header card */
.module-header-card {
  padding: 20px 24px;
}

.module-header-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.module-header-actions {
  display: flex;
  align-items: center;
  gap: 10px;
}

.module-stat-tag {
  font-size: 12px;
  padding: 4px 12px;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.06);
  color: #627284;
}

.accent-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: none;
  border-radius: 999px;
  background: #ba5c3d;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 6px 16px rgba(186, 92, 61, 0.14);
  transition: transform 0.15s ease, box-shadow 0.15s ease, opacity 0.15s ease;
}

.accent-button:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(186, 92, 61, 0.2);
}

.accent-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Search bar */
.search-bar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid rgba(23, 32, 42, 0.05);
  background: rgba(252, 250, 245, 0.5);
  border-radius: 22px 22px 0 0;
}

.search-fields {
  display: flex;
  gap: 10px;
  flex: 1;
}

.search-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
  flex: 1;
}

.search-field span {
  font-size: 11px;
  color: #8a9bab;
  letter-spacing: 0.04em;
}

.search-field input {
  padding: 7px 12px;
  border-radius: 10px;
  font-size: 13px;
  border: 1px solid rgba(23, 32, 42, 0.1);
  background: #fff;
  color: #17202a;
}

.search-field input:focus {
  outline: none;
  border-color: #ba5c3d;
  box-shadow: 0 0 0 3px rgba(186, 92, 61, 0.08);
}

.search-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.search-button {
  padding: 7px 18px;
  border: none;
  border-radius: 999px;
  background: #213a4f;
  color: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: transform 0.15s ease, opacity 0.15s ease;
}

.search-button:hover:not(:disabled) {
  transform: translateY(-1px);
}

.search-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.reset-button {
  padding: 7px 14px;
  border: none;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.07);
  color: #213a4f;
  font-size: 13px;
  cursor: pointer;
  transition: background 0.15s ease, opacity 0.15s ease;
}

.reset-button:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.12);
}

.reset-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Table */
.module-table-wrap {
  overflow: auto;
  padding: 0;
}

.module-table {
  width: 100%;
  border-collapse: collapse;
}

.module-table th {
  padding: 10px 12px;
  text-align: left;
  font-size: 11px;
  font-weight: 600;
  color: #627284;
  background: rgba(252, 250, 245, 0.7);
  border-bottom: 1px solid rgba(23, 32, 42, 0.06);
  letter-spacing: 0.03em;
  white-space: nowrap;
}

.module-table td {
  padding: 6px 10px;
  border-bottom: 1px solid rgba(23, 32, 42, 0.04);
  vertical-align: top;
}

.module-table tbody tr:hover {
  background: rgba(252, 250, 245, 0.5);
}

.module-table tbody tr:last-child td {
  border-bottom: none;
}

.module-cell-merged {
  background: rgba(252, 250, 245, 0.4);
  font-weight: 500;
  vertical-align: middle !important;
}

.table-input {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  font-size: 12px;
  color: #17202a;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.table-input:hover {
  border-color: rgba(23, 32, 42, 0.08);
}

.table-input:focus {
  outline: none;
  border-color: #ba5c3d;
  background: #fff;
  box-shadow: 0 0 0 2px rgba(186, 92, 61, 0.06);
}

.table-textarea {
  width: 100%;
  padding: 5px 8px;
  border: 1px solid transparent;
  border-radius: 6px;
  background: transparent;
  font-size: 12px;
  color: #17202a;
  resize: vertical;
  font-family: inherit;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.table-textarea:hover {
  border-color: rgba(23, 32, 42, 0.08);
}

.table-textarea:focus {
  outline: none;
  border-color: #ba5c3d;
  background: #fff;
  box-shadow: 0 0 0 2px rgba(186, 92, 61, 0.06);
}

.module-cell-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px 10px;
}

.save-button {
  padding: 4px 12px;
  border: none;
  border-radius: 8px;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.save-button:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.15);
}

.save-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.delete-button {
  padding: 4px 12px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #8a1f28;
  font-size: 11px;
  cursor: pointer;
  transition: background 0.15s ease;
}

.delete-button:hover:not(:disabled) {
  background: rgba(138, 31, 40, 0.06);
}

.delete-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Pagination */
.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 12px 20px 16px;
}

.page-button {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: rgba(33, 58, 79, 0.06);
  color: #213a4f;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease;
}

.page-button:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.12);
}

.page-button:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.page-label {
  font-size: 12px;
  color: #627284;
}

.page-label strong {
  color: #17202a;
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 40px 20px;
  color: #8a9bab;
  text-align: center;
  font-size: 13px;
}

/* Modal */
.modal-card {
  padding: 24px;
  width: min(640px, 100%);
  max-height: calc(100vh - 80px);
  overflow: auto;
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.close-button {
  width: 32px;
  height: 32px;
  border: none;
  border-radius: 8px;
  background: rgba(33, 58, 79, 0.06);
  color: #627284;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.15s ease, color 0.15s ease;
}

.close-button:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.12);
  color: #17202a;
}

.close-button:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

.modal-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.form-field--wide {
  grid-column: 1 / -1;
}

.form-field span {
  font-size: 11px;
  color: #8a9bab;
  letter-spacing: 0.04em;
}

.form-field input,
.form-field textarea {
  padding: 8px 12px;
  border: 1px solid rgba(23, 32, 42, 0.1);
  border-radius: 10px;
  background: #fff;
  color: #17202a;
  font-size: 13px;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: #ba5c3d;
  box-shadow: 0 0 0 3px rgba(186, 92, 61, 0.08);
}

.form-field textarea {
  resize: vertical;
  font-family: inherit;
}

.modal-footer {
  display: flex;
  gap: 8px;
  margin-top: 18px;
}

@media (max-width: 1180px) {
  .search-fields {
    flex-direction: column;
  }
}

@media (max-width: 860px) {
  .module-header-row {
    flex-direction: column;
  }

  .search-bar {
    flex-direction: column;
    align-items: stretch;
  }

  .search-actions {
    justify-content: flex-end;
  }
}
</style>
