<script setup>
import { computed, onMounted, ref } from "vue";

import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();

const LEVEL_COLUMNS = [
  { key: "unmarked", label: "未标注" },
  { key: "unfamiliar", label: "不了解" },
  { key: "aware", label: "了解" },
  { key: "familiar", label: "熟悉" },
];
const LEVEL_LABEL_BY_KEY = {
  unfamiliar: "不了解",
  aware: "了解",
  familiar: "熟悉",
};
const LEVEL_KEY_BY_LABEL = {
  不了解: "unfamiliar",
  了解: "aware",
  熟悉: "familiar",
};

const memberForms = computed(() => {
  const members = workspaceStore.workspace.managed_members;
  return (members || []).map((member) => createMemberForm(member));
});

const newMember = ref(createMemberForm());
const showMemberModuleModal = ref(false);
const selectedMemberName = ref("");
const draggingModuleKey = ref("");
const dragSourceLevel = ref("");
const dragHoverLevel = ref("");
const savingModuleKey = ref("");
const pendingMemberLevelOverrides = ref({});
const memberModuleBoard = computed(() => buildMemberModuleBoard(selectedMemberName.value));

const memberCount = computed(() => workspaceStore.workspace.managed_members.length);

function createMemberForm(member = {}) {
  return {
    original_name: member.name || "",
    name: member.name || "",
    role: member.role || "developer",
    skills_text: Array.isArray(member.skills) ? member.skills.join(", ") : "",
    experience: member.experience_level || "中",
    workload: member.workload ?? 0,
    capacity: member.capacity ?? 1,
    constraints_text: Array.isArray(member.constraints) ? member.constraints.join(", ") : "",
  };
}

function memberPayload(form) {
  return {
    name: form.name,
    role: form.role,
    skills: form.skills_text,
    experience: form.experience,
    workload: Number(form.workload) || 0,
    capacity: Number(form.capacity) || 0,
    constraints: form.constraints_text,
  };
}

function normalizeName(value) {
  return String(value || "").trim().toLowerCase();
}

function normalizeLevel(value) {
  const level = String(value || "").trim();
  if (level === "一般") {
    return "了解";
  }
  return level;
}

function uniqueNames(values) {
  const sourceValues = Array.isArray(values) ? values : String(values || "").split(/[\n,，;；、/]+/);
  const names = [];
  sourceValues
    .map((item) => String(item || "").trim())
    .filter(Boolean)
    .forEach((name) => {
      if (!names.includes(name)) {
        names.push(name);
      }
    });
  return names;
}

function resolveModuleKey(entry) {
  return String(entry.key || `${entry.big_module || ""}::${entry.function_module || ""}`).trim();
}

function resolveEntryFamiliarityItems(entry) {
  const byNormalized = new Map();
  const addItem = (name, level) => {
    const cleanName = String(name || "").trim();
    const cleanLevel = normalizeLevel(level);
    const normalized = normalizeName(cleanName);
    if (!normalized || !["熟悉", "了解", "不了解"].includes(cleanLevel)) {
      return;
    }
    byNormalized.set(normalized, {
      normalized,
      name: cleanName,
      level: cleanLevel,
    });
  };
  const unfamiliar = uniqueNames(entry.unfamiliar_members);
  const aware = uniqueNames(entry.aware_members);
  const familiar = uniqueNames(entry.familiar_members);
  const hasGroupedFields = unfamiliar.length > 0 || aware.length > 0 || familiar.length > 0;

  if (hasGroupedFields) {
    unfamiliar.forEach((name) => addItem(name, "不了解"));
    aware.forEach((name) => addItem(name, "了解"));
    familiar.forEach((name) => addItem(name, "熟悉"));
    return Array.from(byNormalized.values());
  }

  Object.entries(entry.familiarity_by_member || {}).forEach(([name, level]) => {
    addItem(name, level);
  });
  return Array.from(byNormalized.values());
}

function resolveEntryFamiliarityMap(entry) {
  const familiarityMap = {};
  resolveEntryFamiliarityItems(entry).forEach((item) => {
    familiarityMap[item.normalized] = item.level;
  });
  return familiarityMap;
}

function resolveBackupOwners(entry) {
  const names = uniqueNames(entry.backup_owners);
  if (names.length) {
    return names.join(", ");
  }
  const fallback = String(entry.backup_owner || "").trim();
  return fallback || "-";
}

function resolveMemberLevel(entry, memberName) {
  const moduleKey = resolveModuleKey(entry);
  const overrideLevel = pendingMemberLevelOverrides.value[moduleKey];
  if (overrideLevel) {
    return overrideLevel;
  }
  const normalizedMemberName = normalizeName(memberName);
  if (!normalizedMemberName) {
    return "unmarked";
  }
  const level = resolveEntryFamiliarityMap(entry)[normalizedMemberName];
  return LEVEL_KEY_BY_LABEL[level] || "unmarked";
}

function toModuleCard(entry, level) {
  return {
    key: resolveModuleKey(entry),
    level,
    big_module: entry.big_module || "-",
    function_module: entry.function_module || "-",
    primary_owner: entry.primary_owner || "-",
    backup_owners: resolveBackupOwners(entry),
  };
}

function buildMemberModuleBoard(memberName) {
  const grouped = {
    unmarked: [],
    unfamiliar: [],
    aware: [],
    familiar: [],
  };
  const entries = Array.isArray(workspaceStore.workspace.module_entries) ? workspaceStore.workspace.module_entries : [];
  entries.forEach((entry) => {
    const level = resolveMemberLevel(entry, memberName);
    if (!grouped[level]) {
      grouped.unmarked.push(toModuleCard(entry, "unmarked"));
      return;
    }
    grouped[level].push(toModuleCard(entry, level));
  });
  return grouped;
}

function buildPayloadForLevelChange(entry, memberName, targetLevel) {
  const familiarityByMember = new Map();
  resolveEntryFamiliarityItems(entry).forEach((item) => {
    familiarityByMember.set(item.normalized, item);
  });
  const normalizedMemberName = normalizeName(memberName);
  familiarityByMember.delete(normalizedMemberName);
  const targetLabel = LEVEL_LABEL_BY_KEY[targetLevel];
  const cleanMemberName = String(memberName || "").trim();
  if (targetLabel && cleanMemberName) {
    familiarityByMember.set(normalizedMemberName, {
      normalized: normalizedMemberName,
      name: cleanMemberName,
      level: targetLabel,
    });
  }

  const familiar_members = [];
  const aware_members = [];
  const unfamiliar_members = [];
  familiarityByMember.forEach((item) => {
    if (item.level === "熟悉") {
      familiar_members.push(item.name);
      return;
    }
    if (item.level === "了解") {
      aware_members.push(item.name);
      return;
    }
    if (item.level === "不了解") {
      unfamiliar_members.push(item.name);
    }
  });

  return {
    big_module: entry.big_module || "",
    function_module: entry.function_module || "",
    primary_owner: entry.primary_owner || "",
    backup_owners: uniqueNames(entry.backup_owners || (entry.backup_owner ? [entry.backup_owner] : [])),
    familiar_members,
    aware_members,
    unfamiliar_members,
  };
}

function resetDragState() {
  draggingModuleKey.value = "";
  dragSourceLevel.value = "";
  dragHoverLevel.value = "";
  savingModuleKey.value = "";
  pendingMemberLevelOverrides.value = {};
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

function findModuleEntryByKey(moduleKey) {
  const entries = Array.isArray(workspaceStore.workspace.module_entries) ? workspaceStore.workspace.module_entries : [];
  return entries.find((entry) => resolveModuleKey(entry) === moduleKey) || null;
}

function canDragEntry(moduleKey) {
  return Boolean(moduleKey) && !workspaceStore.loading && !savingModuleKey.value;
}

function onDragStart(moduleKey, sourceLevel) {
  if (!canDragEntry(moduleKey)) {
    return;
  }
  draggingModuleKey.value = moduleKey;
  dragSourceLevel.value = sourceLevel;
  dragHoverLevel.value = sourceLevel;
}

function onDragOver(targetLevel) {
  if (!draggingModuleKey.value || savingModuleKey.value) {
    return;
  }
  dragHoverLevel.value = targetLevel;
}

function onDragEnd() {
  dragHoverLevel.value = "";
}

async function onDrop(targetLevel) {
  const moduleKey = draggingModuleKey.value;
  const sourceLevel = dragSourceLevel.value;
  dragHoverLevel.value = "";
  if (!moduleKey || !sourceLevel || !selectedMemberName.value) {
    draggingModuleKey.value = "";
    dragSourceLevel.value = "";
    return;
  }
  if (sourceLevel === targetLevel) {
    draggingModuleKey.value = "";
    dragSourceLevel.value = "";
    return;
  }
  const entry = findModuleEntryByKey(moduleKey);
  if (!entry) {
    draggingModuleKey.value = "";
    dragSourceLevel.value = "";
    return;
  }

  pendingMemberLevelOverrides.value = {
    ...pendingMemberLevelOverrides.value,
    [moduleKey]: targetLevel,
  };
  savingModuleKey.value = moduleKey;
  try {
    await workspaceStore.updateModule(moduleKey, {
      ...buildPayloadForLevelChange(entry, selectedMemberName.value, targetLevel),
      original_key: moduleKey,
    });
    await workspaceStore.refreshMembers();
    notifyActionResult(true, "已更新成员模块熟悉度");
  } catch (error) {
    notifyActionResult(false, error instanceof Error ? error.message : "更新成员模块熟悉度失败");
  } finally {
    const nextOverrides = {
      ...pendingMemberLevelOverrides.value,
    };
    delete nextOverrides[moduleKey];
    pendingMemberLevelOverrides.value = nextOverrides;
    savingModuleKey.value = "";
    draggingModuleKey.value = "";
    dragSourceLevel.value = "";
  }
}

onMounted(() => {
  workspaceStore.refreshMembers();
});

async function createManagedMember() {
  await workspaceStore.createMember(memberPayload(newMember.value));
  newMember.value = createMemberForm();
}

async function saveManagedMember(form) {
  await workspaceStore.updateMember(form.original_name, memberPayload(form));
}

async function deleteManagedMember(form) {
  await workspaceStore.deleteMember(form.original_name);
}

function openMemberModuleModal(form) {
  resetDragState();
  selectedMemberName.value = form.name || form.original_name || "";
  showMemberModuleModal.value = true;
}

function closeMemberModuleModal() {
  resetDragState();
  selectedMemberName.value = "";
  showMemberModuleModal.value = false;
}
</script>

<template>
  <section class="personnel-page">
    <!-- Header card -->
    <article class="personnel-header">
      <div class="header-content">
        <div>
          <p class="section-kicker">Personnel</p>
          <h2 class="page-title">人员管理</h2>
        </div>
        <span class="stat-tag">{{ memberCount }} 位成员</span>
      </div>
      <p class="header-hint">人员管理页是推荐、监控和团队洞察的唯一成员来源。</p>
    </article>

    <!-- Add new member -->
    <article class="add-member-card">
      <div class="card-head">
        <h3>新增成员画像</h3>
        <svg class="add-icon" viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
          <path d="M10 4v12M4 10h12" />
        </svg>
      </div>
      <form class="add-form" @submit.prevent="createManagedMember">
        <div class="add-grid">
          <label class="field">
            <span>姓名</span>
            <input v-model="newMember.name" placeholder="例如：李祥" />
          </label>
          <label class="field">
            <span>角色</span>
            <select v-model="newMember.role">
              <option value="developer">开发</option>
              <option value="tester">测试</option>
              <option value="qa">QA</option>
              <option value="test">Test</option>
            </select>
          </label>
          <label class="field">
            <span>技能</span>
            <input v-model="newMember.skills_text" placeholder="发票, 接口, 税务" />
          </label>
          <label class="field">
            <span>经验</span>
            <input v-model="newMember.experience" placeholder="高 / 中 / 中高" />
          </label>
          <label class="field">
            <span>负载</span>
            <input v-model="newMember.workload" type="number" step="0.1" min="0" />
          </label>
          <label class="field">
            <span>容量</span>
            <input v-model="newMember.capacity" type="number" step="0.1" min="0.1" />
          </label>
          <label class="field field-wide">
            <span>约束</span>
            <input v-model="newMember.constraints_text" placeholder="不可分配夜间需求, 仅负责测试" />
          </label>
        </div>
        <div class="add-actions">
          <button class="primary-button" type="submit" :disabled="workspaceStore.loading">新增成员</button>
        </div>
      </form>
      <p v-if="workspaceStore.error" class="error-text">{{ workspaceStore.error }}</p>
    </article>

    <!-- Member roster table -->
    <article class="roster-card">
      <div class="card-head">
        <h3>已维护成员</h3>
        <span class="soft-tag soft-tag-light">{{ memberCount }} 人</span>
      </div>

      <div v-if="memberForms.length" class="table-wrap">
        <table class="roster-table">
          <thead>
            <tr>
              <th>姓名</th>
              <th>角色</th>
              <th>技能</th>
              <th>经验</th>
              <th>负载</th>
              <th>容量</th>
              <th>约束</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="form in memberForms" :key="form.original_name">
              <td><input class="table-input" v-model="form.name" /></td>
              <td>
                <select class="table-input" v-model="form.role">
                  <option value="developer">开发</option>
                  <option value="tester">测试</option>
                  <option value="qa">QA</option>
                  <option value="test">Test</option>
                </select>
              </td>
              <td><input class="table-input" v-model="form.skills_text" /></td>
              <td><input class="table-input" v-model="form.experience" /></td>
              <td><input class="table-input" v-model="form.workload" type="number" step="0.1" min="0" /></td>
              <td><input class="table-input" v-model="form.capacity" type="number" step="0.1" min="0.1" /></td>
              <td><input class="table-input" v-model="form.constraints_text" /></td>
              <td class="row-actions">
                <button class="btn-save" :disabled="workspaceStore.loading" @click="saveManagedMember(form)">保存</button>
                <button class="btn-modules" :disabled="workspaceStore.loading" @click="openMemberModuleModal(form)">模块</button>
                <button class="btn-delete" :disabled="workspaceStore.loading" @click="deleteManagedMember(form)">删除</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-state">
        <svg viewBox="0 0 64 64" width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="32" cy="20" r="10" />
          <path d="M14 54c0-10 8-18 18-18s18 8 18 18" />
          <path d="M44 14l6 6M50 14l-6 6" />
        </svg>
        <p>当前还没有维护任何成员，先新增团队画像。</p>
      </div>
    </article>

    <!-- Module familiarity modal -->
    <div v-if="showMemberModuleModal" class="modal-backdrop" @click.self="closeMemberModuleModal">
      <section class="modal-card">
        <div class="modal-head">
          <div>
            <p class="section-kicker">Member Modules</p>
            <h3>模块熟悉度 — {{ selectedMemberName }}</h3>
          </div>
          <button class="modal-close" @click="closeMemberModuleModal">
            <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
        </div>

        <div class="board-grid">
          <article
            v-for="column in LEVEL_COLUMNS"
            :key="column.key"
            class="board-column"
            :class="{ 'is-drop-target': dragHoverLevel === column.key && !!draggingModuleKey }"
            :data-column-key="column.key"
            @dragover.prevent="onDragOver(column.key)"
            @drop.prevent="onDrop(column.key)"
          >
            <div class="col-head">
              <h4>{{ column.label }}</h4>
              <span class="col-count">{{ memberModuleBoard[column.key].length }}</span>
            </div>
            <div v-if="memberModuleBoard[column.key].length" class="col-list">
              <article
                v-for="entry in memberModuleBoard[column.key]"
                :key="entry.key"
                class="module-chip"
                :class="{
                  'is-dragging': draggingModuleKey === entry.key,
                  'is-saving': savingModuleKey === entry.key,
                }"
                :draggable="canDragEntry(entry.key)"
                :data-module-key="entry.key"
                :data-level-key="column.key"
                @dragstart="onDragStart(entry.key, column.key)"
                @dragend="onDragEnd"
              >
                <p class="chip-title">{{ entry.big_module }} / {{ entry.function_module }}</p>
                <p class="chip-meta">负责人：{{ entry.primary_owner }}</p>
                <p class="chip-meta">B角：{{ entry.backup_owners }}</p>
                <p v-if="savingModuleKey === entry.key" class="chip-saving">保存中...</p>
              </article>
            </div>
            <p v-else class="col-empty">暂无模块</p>
          </article>
        </div>
      </section>
    </div>
  </section>
</template>

<style scoped>
.personnel-page {
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
.personnel-header {
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

.stat-tag {
  padding: 5px 14px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  background: rgba(58, 138, 92, 0.1);
  color: #2a6b48;
  flex-shrink: 0;
  margin-top: 6px;
}

.header-hint {
  margin: 0;
  font-size: 13px;
  color: #8a9bab;
  line-height: 1.5;
}

/* Add member card */
.add-member-card {
  padding: 22px 24px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
}

.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
}

.card-head h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #17202a;
  font-family: Georgia, "Times New Roman", serif;
}

.add-icon {
  color: #ba5c3d;
}

.add-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.add-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field span {
  font-size: 12px;
  color: #627284;
  font-weight: 600;
}

.field-wide {
  grid-column: 1 / -1;
}

.add-actions {
  display: flex;
  justify-content: flex-end;
}

.error-text {
  margin: 12px 0 0;
  color: #8a1f28;
  font-size: 12px;
  font-weight: 600;
  background: rgba(138, 31, 40, 0.04);
  padding: 8px 14px;
  border-radius: 12px;
}

/* Roster card */
.roster-card {
  padding: 22px 24px;
  background: rgba(255, 255, 255, 0.94);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 14px 42px rgba(28, 46, 64, 0.07);
}

.table-wrap {
  overflow: auto;
  border-radius: 16px;
  border: 1px solid #e8edf3;
  background: #fff;
}

.roster-table {
  width: 100%;
  border-collapse: collapse;
}

.roster-table th,
.roster-table td {
  padding: 10px 12px;
  text-align: left;
  border-bottom: 1px solid #f0f3f7;
  vertical-align: middle;
  white-space: nowrap;
}

.roster-table th {
  color: #627284;
  background: #fafbfc;
  font-weight: 700;
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.roster-table tbody tr {
  transition: background 0.15s ease;
}

.roster-table tbody tr:hover {
  background: rgba(255, 248, 235, 0.4);
}

.roster-table tbody tr:last-child td {
  border-bottom: none;
}

.table-input {
  width: 100%;
  border: 1px solid transparent;
  border-radius: 10px;
  padding: 7px 10px;
  background: transparent;
  color: #17202a;
  font-size: 13px;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.table-input:hover {
  border-color: #dce4ed;
  background: #fff;
}

.table-input:focus {
  outline: none;
  border-color: #ba5c3d;
  box-shadow: 0 0 0 2px rgba(186, 92, 61, 0.1);
  background: #fff;
}

.row-actions {
  white-space: nowrap;
}

.row-actions button {
  border: none;
  border-radius: 999px;
  padding: 5px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  margin-right: 6px;
}

.row-actions button:last-child {
  margin-right: 0;
}

.btn-save {
  background: #213a4f;
  color: #fff;
}

.btn-save:hover:not(:disabled) {
  background: #2a4a62;
}

.btn-modules {
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
}

.btn-modules:hover:not(:disabled) {
  background: rgba(33, 58, 79, 0.14);
}

.btn-delete {
  background: transparent;
  color: #8a1f28;
}

.btn-delete:hover:not(:disabled) {
  background: rgba(138, 31, 40, 0.06);
}

/* Empty state */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 20px;
  color: #8a9bab;
  text-align: center;
  font-size: 14px;
}

.empty-state svg {
  opacity: 0.4;
}

/* Modal */
.modal-card {
  width: min(900px, 100%);
  max-height: calc(100vh - 60px);
  overflow: auto;
  padding: 24px;
  background: rgba(255, 255, 255, 0.96);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(28, 46, 64, 0.12);
  animation: modalFadeIn 0.25s ease both;
}

@keyframes modalFadeIn {
  from { opacity: 0; transform: scale(0.97) translateY(6px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

.modal-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
}

.modal-head h3 {
  margin: 0;
  font-size: 20px;
  font-family: Georgia, "Times New Roman", serif;
  color: #17202a;
}

.modal-close {
  border: none;
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
  width: 34px;
  height: 34px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease;
  flex-shrink: 0;
}

.modal-close:hover {
  background: rgba(33, 58, 79, 0.14);
}

/* Board grid */
.board-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.board-column {
  border-radius: 16px;
  padding: 14px;
  background: #f8fafc;
  border: 2px solid transparent;
  min-height: 180px;
  transition: all 0.2s ease;
}

.board-column[data-column-key="unfamiliar"] {
  background: rgba(138, 31, 40, 0.03);
}

.board-column[data-column-key="aware"] {
  background: rgba(186, 140, 61, 0.04);
}

.board-column[data-column-key="familiar"] {
  background: rgba(58, 138, 92, 0.04);
}

.board-column.is-drop-target {
  border-color: #ba5c3d;
  background: #fff8f3;
  box-shadow: 0 0 0 3px rgba(186, 92, 61, 0.1);
}

.col-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 12px;
}

.col-head h4 {
  margin: 0;
  font-size: 14px;
  font-weight: 700;
  color: #17202a;
}

.col-count {
  font-size: 11px;
  padding: 2px 10px;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.08);
  color: #627284;
  font-weight: 600;
}

.col-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.module-chip {
  padding: 10px 12px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e8edf3;
  cursor: grab;
  transition: all 0.18s ease;
}

.module-chip:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(25, 47, 68, 0.07);
}

.module-chip.is-dragging {
  opacity: 0.4;
}

.module-chip.is-saving {
  opacity: 0.7;
  cursor: progress;
}

.chip-title {
  margin: 0 0 6px;
  font-size: 13px;
  font-weight: 700;
  color: #17202a;
  line-height: 1.3;
}

.chip-meta {
  margin: 0;
  font-size: 11px;
  color: #8a9bab;
  line-height: 1.4;
}

.chip-saving {
  margin: 6px 0 0;
  font-size: 11px;
  color: #ba5c3d;
  font-weight: 600;
}

.col-empty {
  margin: 16px 0 0;
  color: #a0b0c0;
  font-size: 12px;
  text-align: center;
}

@media (max-width: 1180px) {
  .add-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .board-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .add-grid {
    grid-template-columns: 1fr;
  }

  .header-content {
    flex-direction: column;
  }

  .board-grid {
    grid-template-columns: 1fr;
  }

  .roster-table {
    font-size: 12px;
  }
}
</style>
