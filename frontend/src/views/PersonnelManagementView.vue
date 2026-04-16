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
  "不了解": "unfamiliar",
  "了解": "aware",
  "熟悉": "familiar",
};

const memberForms = computed(() => {
  const members = workspaceStore.workspace.managed_members;
  return (members || []).map((member) => createMemberForm(member));
});

const newMember = ref(createMemberForm());
const showAddForm = ref(false);
const showMemberModuleModal = ref(false);
const selectedMemberName = ref("");
const draggingModuleKey = ref("");
const dragSourceLevel = ref("");
const dragHoverLevel = ref("");
const savingModuleKey = ref("");
const pendingMemberLevelOverrides = ref({});
const memberModuleBoard = computed(() => buildMemberModuleBoard(selectedMemberName.value));
const editingMemberKey = ref("");

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
    // no-op
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
  if (!newMember.value.name.trim()) return;
  await workspaceStore.createMember(memberPayload(newMember.value));
  newMember.value = createMemberForm();
  showAddForm.value = false;
}

async function saveManagedMember(form) {
  await workspaceStore.updateMember(form.original_name, memberPayload(form));
  editingMemberKey.value = "";
}

async function deleteManagedMember(form) {
  if (!confirm(`确定删除成员「${form.name}」？`)) return;
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

function startEditMember(form) {
  editingMemberKey.value = form.original_name;
}

function cancelEditMember(form) {
  // Reset form to original values
  const orig = workspaceStore.workspace.managed_members.find(
    (m) => m.name === form.original_name
  );
  if (orig) {
    Object.assign(form, createMemberForm(orig));
  }
  editingMemberKey.value = "";
}

// Role display helpers
const ROLE_LABELS = {
  developer: "开发",
  tester: "测试",
  qa: "QA",
  test: "Test",
};

function roleBadgeClass(role) {
  switch (role) {
    case "developer": return "badge-dev";
    case "tester": return "badge-tester";
    case "qa": return "badge-qa";
    case "test": return "badge-test";
    default: return "badge-dev";
  }
}

// Workload bar color
function workloadColor(workload, capacity) {
  const ratio = capacity > 0 ? workload / capacity : 0;
  if (ratio > 0.9) return "#8a1f28";
  if (ratio > 0.7) return "#ba5c3d";
  if (ratio > 0.4) return "#ba8c3d";
  return "#3a8a5c";
}
</script>

<template>
  <section class="personnel-page">
    <!-- Header -->
    <header class="page-header">
      <div class="header-left">
        <span class="kicker">Team</span>
        <h1>人员管理</h1>
      </div>
      <div class="header-right">
        <span class="member-pill">{{ memberCount }} 位成员</span>
      </div>
    </header>

    <!-- Add member trigger / inline form -->
    <article class="add-member-section" :class="{ 'is-open': showAddForm }">
      <div v-if="!showAddForm" class="add-trigger" @click="showAddForm = true">
        <svg viewBox="0 0 20 20" width="22" height="22" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
          <path d="M10 4v12M4 10h12" />
        </svg>
        <span>新增成员</span>
      </div>
      <form v-else class="member-form-card" @submit.prevent="createManagedMember">
        <div class="form-head">
          <h3>新增成员画像</h3>
          <button type="button" class="icon-btn" @click="showAddForm = false">
            <svg viewBox="0 0 20 20" width="18" height="18" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
              <path d="M5 5l10 10M15 5L5 15" />
            </svg>
          </button>
        </div>
        <div class="form-grid">
          <label class="field">
            <span>姓名</span>
            <input v-model="newMember.name" placeholder="例如：李祥" required autofocus />
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
            <input v-model="newMember.experience" placeholder="高 / 中 / 低" />
          </label>
          <label class="field">
            <span>当前负载</span>
            <input v-model="newMember.workload" type="number" step="0.1" min="0" />
          </label>
          <label class="field">
            <span>容量系数</span>
            <input v-model="newMember.capacity" type="number" step="0.1" min="0.1" />
          </label>
          <label class="field field-wide">
            <span>约束</span>
            <input v-model="newMember.constraints_text" placeholder="不可分配夜间需求, 仅负责测试" />
          </label>
        </div>
        <div class="form-actions">
          <button type="button" class="btn-ghost" @click="showAddForm = false">取消</button>
          <button type="submit" class="btn-primary" :disabled="workspaceStore.loading">确认新增</button>
        </div>
        <p v-if="workspaceStore.error" class="form-error">{{ workspaceStore.error }}</p>
      </form>
    </article>

    <!-- Member roster: table -->
    <div v-if="memberForms.length" class="roster-table-wrap">
      <table class="roster-table">
        <thead>
          <tr>
            <th class="col-name">姓名</th>
            <th class="col-role">角色</th>
            <th class="col-skills">技能</th>
            <th class="col-exp">经验</th>
            <th class="col-load">负载</th>
            <th class="col-capacity">容量</th>
            <th class="col-constraints">约束</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="form in memberForms" :key="form.original_name" :class="{ 'is-editing': editingMemberKey === form.original_name }">
            <td class="col-name">
              <template v-if="editingMemberKey === form.original_name">
                <input class="cell-input" v-model="form.name" placeholder="姓名" />
              </template>
              <template v-else>
                {{ form.name }}
              </template>
            </td>
            <td class="col-role">
              <span class="role-badge" :class="roleBadgeClass(form.role)">
                {{ ROLE_LABELS[form.role] || form.role }}
              </span>
            </td>
            <td class="col-skills">
              <template v-if="editingMemberKey === form.original_name">
                <input class="cell-input" v-model="form.skills_text" placeholder="发票, 接口, 税务" />
              </template>
              <template v-else>
                <span v-if="form.skills_text" class="skill-tag" v-for="s in form.skills_text.split(/[,，、\s]+/).filter(Boolean)" :key="s">{{ s }}</span>
                <span v-else class="no-data">—</span>
              </template>
            </td>
            <td class="col-exp">
              <template v-if="editingMemberKey === form.original_name">
                <input class="cell-input cell-sm" v-model="form.experience" />
              </template>
              <template v-else>
                {{ form.experience }}
              </template>
            </td>
            <td class="col-load">
              <template v-if="editingMemberKey === form.original_name">
                <input class="cell-input cell-sm" v-model="form.workload" type="number" step="0.1" min="0" />
              </template>
              <template v-else>
                <div class="load-bar-track">
                  <div
                    class="load-bar-fill"
                    :style="{ width: Math.min(100, (Number(form.workload) / (Number(form.capacity) || 1)) * 100) + '%', background: workloadColor(Number(form.workload), Number(form.capacity)) }"
                  />
                </div>
                <span class="load-val">{{ Number(form.workload).toFixed(1) }} / {{ Number(form.capacity).toFixed(1) }}</span>
              </template>
            </td>
            <td class="col-capacity">
              <template v-if="editingMemberKey === form.original_name">
                <input class="cell-input cell-sm" v-model="form.capacity" type="number" step="0.1" min="0.1" />
              </template>
              <template v-else>
                {{ Number(form.capacity).toFixed(1) }}
              </template>
            </td>
            <td class="col-constraints">
              <template v-if="editingMemberKey === form.original_name">
                <input class="cell-input" v-model="form.constraints_text" placeholder="约束说明" />
              </template>
              <template v-else>
                <span v-if="form.constraints_text">{{ form.constraints_text }}</span>
                <span v-else class="no-data">—</span>
              </template>
            </td>
            <td class="col-actions">
              <template v-if="editingMemberKey === form.original_name">
                <button class="action-btn action-save" @click="saveManagedMember(form)">保存</button>
                <button class="action-btn action-cancel" @click="cancelEditMember(form)">取消</button>
              </template>
              <template v-else>
                <button class="action-btn action-edit" @click="startEditMember(form)">编辑</button>
                <button class="action-btn action-modules" @click="openMemberModuleModal(form)">模块</button>
                <button class="action-btn action-delete" @click="deleteManagedMember(form)">删除</button>
              </template>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Empty state -->
    <div v-else class="empty-roster">
      <div class="empty-illustration">
        <svg viewBox="0 0 120 120" width="100" height="100" fill="none" stroke="currentColor" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="60" cy="42" r="22" />
          <path d="M24 100c0-20 16-36 36-36s36 16 36 36" />
          <line x1="82" y1="24" x2="96" y2="10" stroke-width="2" />
          <line x1="96" y1="24" x2="82" y2="10" stroke-width="2" />
        </svg>
      </div>
      <h3>还没有成员</h3>
      <p>点击上方「新增成员」开始维护团队画像</p>
    </div>

    <!-- Familiarity modal -->
    <Teleport to="body">
      <div v-if="showMemberModuleModal" class="modal-overlay" @click.self="closeMemberModuleModal">
        <section class="familiarity-modal">
          <header class="modal-header">
            <div>
              <span class="kicker">Module Familiarity</span>
              <h2>{{ selectedMemberName }} 的模块熟悉度</h2>
            </div>
            <button class="close-btn" @click="closeMemberModuleModal">
              <svg viewBox="0 0 20 20" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
                <path d="M5 5l10 10M15 5L5 15" />
              </svg>
            </button>
          </header>

          <div class="kanban-board">
            <div
              v-for="col in LEVEL_COLUMNS"
              :key="col.key"
              class="kanban-lane"
              :class="[`lane-${col.key}`, { 'is-drop-target': dragHoverLevel === col.key && !!draggingModuleKey }]"
              :data-lane-key="col.key"
              @dragover.prevent="onDragOver(col.key)"
              @drop.prevent="onDrop(col.key)"
            >
              <div class="lane-head">
                <span class="lane-dot" :class="`dot-${col.key}`" />
                <h4>{{ col.label }}</h4>
                <span class="lane-count">{{ memberModuleBoard[col.key].length }}</span>
              </div>
              <div class="lane-body">
                <div
                  v-for="card in memberModuleBoard[col.key]"
                  :key="card.key"
                  class="kanban-card"
                  :class="{
                    'is-dragging': draggingModuleKey === card.key,
                    'is-saving': savingModuleKey === card.key,
                  }"
                  :draggable="canDragEntry(card.key)"
                  :data-module-key="card.key"
                  @dragstart="onDragStart(card.key, col.key)"
                  @dragend="onDragEnd"
                >
                  <p class="k-title">{{ card.big_module }}<span class="k-sep">/</span>{{ card.function_module }}</p>
                  <div class="k-meta">
                    <span>负责 {{ card.primary_owner }}</span>
                    <span>B角 {{ card.backup_owners }}</span>
                  </div>
                  <p v-if="savingModuleKey === card.key" class="k-saving">保存中…</p>
                </div>
                <p v-if="!memberModuleBoard[col.key].length" class="lane-empty">暂无</p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </Teleport>
  </section>
</template>

<style scoped>
/* ── Page layout ── */
.personnel-page {
  display: flex;
  flex-direction: column;
  gap: 24px;
  animation: fadeUp 0.4s ease both;
}

@keyframes fadeUp {
  from { opacity: 0; transform: translateY(12px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ── Header ── */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 4px;
  border-bottom: 1px solid rgba(23, 32, 42, 0.06);
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.kicker {
  font-size: 10px;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  font-weight: 700;
  color: #ba8c3d;
}

.page-header h1 {
  margin: 0;
  font-size: 30px;
  font-weight: 700;
  color: #17202a;
  font-family: Georgia, "Noto Serif SC", serif;
  letter-spacing: 0.01em;
}

.member-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(58, 138, 92, 0.1) 0%, rgba(58, 138, 92, 0.05) 100%);
  color: #2a6b48;
  font-size: 13px;
  font-weight: 600;
}

/* ── Add member section ── */
.add-member-section {
  border-radius: 20px;
  overflow: hidden;
  transition: all 0.3s ease;
}

.add-trigger {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 24px;
  background: linear-gradient(135deg, rgba(255, 248, 235, 0.6) 0%, rgba(255, 255, 255, 0.8) 100%);
  border: 1.5px dashed rgba(186, 92, 61, 0.25);
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s ease;
  font-size: 14px;
  color: #627284;
  font-weight: 500;
}

.add-trigger:hover {
  border-color: rgba(186, 92, 61, 0.45);
  background: rgba(255, 248, 235, 0.85);
  color: #ba5c3d;
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(186, 92, 61, 0.08);
}

.add-trigger svg {
  flex-shrink: 0;
  transition: transform 0.2s ease;
}

.add-trigger:hover svg {
  transform: rotate(90deg);
}

/* Form card */
.member-form-card {
  padding: 24px;
  background: #fff;
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(28, 46, 64, 0.07);
  animation: slideOpen 0.3s ease both;
}

@keyframes slideOpen {
  from { opacity: 0; transform: translateY(-8px) scale(0.98); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.form-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 20px;
}

.form-head h3 {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #17202a;
  font-family: Georgia, "Noto Serif SC", serif;
}

.icon-btn {
  border: none;
  background: rgba(33, 58, 79, 0.06);
  color: #627284;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.icon-btn:hover {
  background: rgba(33, 58, 79, 0.12);
  color: #17202a;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 5px;
}

.field span {
  font-size: 11px;
  color: #627284;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.field-wide {
  grid-column: 1 / -1;
}

.field input,
.field select {
  padding: 10px 12px;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  font-size: 14px;
  background: #fafbfc;
  transition: border-color 0.15s ease, background 0.15s ease, box-shadow 0.15s ease;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: #ba5c3d;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(186, 92, 61, 0.08);
}

.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  margin-top: 18px;
}

.btn-ghost {
  border: 1px solid #e2e8f0;
  background: #fff;
  color: #627284;
  padding: 9px 20px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.btn-ghost:hover {
  background: #f7f9fb;
  border-color: #c6d0dc;
  color: #17202a;
}

.btn-primary {
  border: none;
  background: linear-gradient(135deg, #ba5c3d 0%, #a84f32 100%);
  color: #fff;
  padding: 9px 24px;
  border-radius: 999px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 4px 14px rgba(186, 92, 61, 0.2);
  transition: all 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  box-shadow: 0 6px 20px rgba(186, 92, 61, 0.3);
  transform: translateY(-1px);
}

.form-error {
  margin: 12px 0 0;
  color: #8a1f28;
  font-size: 12px;
  font-weight: 600;
  padding: 8px 14px;
  background: rgba(138, 31, 40, 0.04);
  border-radius: 10px;
}

/* ── Roster table ── */
.roster-table-wrap {
  border-radius: 16px;
  overflow: hidden;
  border: 1px solid rgba(23, 32, 42, 0.08);
  background: #fff;
  box-shadow: 0 2px 12px rgba(28, 46, 64, 0.04);
  animation: cardFadeIn 0.35s ease both;
}

@keyframes cardFadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}

.roster-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 14px;
}

.roster-table thead th {
  padding: 12px 14px;
  font-size: 11px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
  color: #8a9bab;
  background: #f8fafc;
  text-align: left;
  border-bottom: 1px solid #e8edf3;
  white-space: nowrap;
}

.roster-table tbody tr {
  transition: background 0.15s ease;
}

.roster-table tbody tr:hover {
  background: #fafbfc;
}

.roster-table tbody tr.is-editing {
  background: rgba(186, 92, 61, 0.02);
}

.roster-table tbody td {
  padding: 12px 14px;
  border-bottom: 1px solid #f0f3f7;
  vertical-align: middle;
  color: #17202a;
}

.roster-table tbody tr:last-child td {
  border-bottom: none;
}

/* Cell input for edit mode */
.cell-input {
  padding: 6px 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 13px;
  background: #fff;
  transition: border-color 0.15s ease, background 0.15s ease;
  width: 100%;
  min-width: 0;
}

.cell-input:focus {
  outline: none;
  border-color: #ba5c3d;
  background: #fff;
}

.cell-sm {
  max-width: 100px;
}

/* Column-specific */
.col-name {
  font-weight: 600;
}

.col-role {
  white-space: nowrap;
}

.col-skills {
  min-width: 140px;
}

.col-exp {
  white-space: nowrap;
  text-align: center;
}

.col-load {
  min-width: 130px;
}

.col-capacity {
  white-space: nowrap;
  text-align: center;
}

.col-constraints {
  min-width: 160px;
  font-size: 13px;
  color: #627284;
  line-height: 1.4;
}

.col-actions {
  white-space: nowrap;
  width: 1%;
}

/* Load bar */
.load-bar-track {
  height: 6px;
  border-radius: 999px;
  background: #eef2f6;
  overflow: hidden;
  margin-bottom: 3px;
}

.load-bar-fill {
  height: 100%;
  border-radius: inherit;
  transition: width 0.3s ease, background 0.3s ease;
}

.load-val {
  font-size: 11px;
  color: #627284;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* Role badge */
.role-badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 11px;
  font-weight: 600;
}

.badge-dev { background: rgba(33, 58, 79, 0.08); color: #213a4f; }
.badge-tester { background: rgba(58, 138, 92, 0.1); color: #2a6b48; }
.badge-qa { background: rgba(186, 140, 61, 0.12); color: #8a6630; }
.badge-test { background: rgba(138, 31, 40, 0.08); color: #8a1f28; }

/* Skill tags */
.skill-tag {
  display: inline-flex;
  padding: 3px 10px;
  border-radius: 999px;
  font-size: 11px;
  background: rgba(33, 58, 79, 0.05);
  color: #4b5b6b;
  margin-right: 4px;
  margin-bottom: 2px;
  white-space: nowrap;
}

.no-data {
  color: #c0cdd8;
}

/* Actions */
.action-btn {
  border: none;
  border-radius: 999px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}

.action-edit {
  background: rgba(33, 58, 79, 0.06);
  color: #213a4f;
}
.action-edit:hover { background: rgba(33, 58, 79, 0.12); }

.action-modules {
  background: rgba(186, 140, 61, 0.08);
  color: #8a6630;
}
.action-modules:hover { background: rgba(186, 140, 61, 0.16); }

.action-save {
  background: linear-gradient(135deg, #213a4f, #2a4a62);
  color: #fff;
}
.action-save:hover { box-shadow: 0 3px 10px rgba(33, 58, 79, 0.2); }

.action-cancel {
  background: #f7f9fb;
  color: #627284;
  border: 1px solid #e2e8f0;
}
.action-cancel:hover { background: #eef2f6; }

.action-delete {
  background: transparent;
  color: #8a1f28;
  padding: 6px 10px;
}
.action-delete:hover { background: rgba(138, 31, 40, 0.06); }

/* ── Empty roster ── */
.empty-roster {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 64px 20px;
  text-align: center;
  animation: fadeUp 0.4s ease both;
}

.empty-illustration {
  color: #c0cdd8;
  margin-bottom: 4px;
}

.empty-roster h3 {
  margin: 0;
  font-size: 18px;
  color: #627284;
  font-family: Georgia, "Noto Serif SC", serif;
}

.empty-roster p {
  margin: 0;
  font-size: 13px;
  color: #8a9bab;
}

/* ── Modal overlay (teleported) ── */
.modal-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: rgba(16, 24, 36, 0.4);
  backdrop-filter: blur(4px);
  animation: overlayIn 0.2s ease both;
}

@keyframes overlayIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.familiarity-modal {
  width: min(960px, 100%);
  max-height: calc(100vh - 48px);
  overflow: auto;
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 24px 72px rgba(0, 0, 0, 0.15);
  animation: modalSlideUp 0.3s ease both;
}

@keyframes modalSlideUp {
  from { opacity: 0; transform: translateY(20px) scale(0.97); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 24px 28px 16px;
}

.modal-header h2 {
  margin: 0;
  font-size: 22px;
  font-weight: 700;
  color: #17202a;
  font-family: Georgia, "Noto Serif SC", serif;
}

.close-btn {
  border: none;
  background: rgba(33, 58, 79, 0.06);
  color: #627284;
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.15s ease;
  flex-shrink: 0;
}

.close-btn:hover {
  background: rgba(33, 58, 79, 0.12);
  color: #17202a;
}

/* ── Kanban board ── */
.kanban-board {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  padding: 0 28px 28px;
}

.kanban-lane {
  border-radius: 16px;
  padding: 14px;
  min-height: 200px;
  background: #f8fafc;
  transition: all 0.2s ease;
  border: 2px solid transparent;
}

.lane-unmarked { background: #f8fafc; }
.lane-unfamiliar { background: rgba(138, 31, 40, 0.02); }
.lane-aware { background: rgba(186, 140, 61, 0.03); }
.lane-familiar { background: rgba(58, 138, 92, 0.03); }

.kanban-lane.is-drop-target {
  border-color: #ba5c3d;
  background: #fff8f3;
  box-shadow: 0 0 0 3px rgba(186, 92, 61, 0.08);
}

.lane-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}

.lane-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.dot-unmarked { background: #c0cdd8; }
.dot-unfamiliar { background: #8a1f28; }
.dot-aware { background: #ba8c3d; }
.dot-familiar { background: #3a8a5c; }

.lane-head h4 {
  margin: 0;
  font-size: 13px;
  font-weight: 700;
  color: #17202a;
  flex: 1;
}

.lane-count {
  font-size: 11px;
  padding: 2px 9px;
  border-radius: 999px;
  background: rgba(33, 58, 79, 0.06);
  color: #8a9bab;
  font-weight: 600;
}

.lane-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.kanban-card {
  padding: 12px;
  border-radius: 12px;
  background: #fff;
  border: 1px solid #e8edf3;
  cursor: grab;
  transition: all 0.2s ease;
}

.kanban-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(25, 47, 68, 0.06);
  border-color: #dce4ed;
}

.kanban-card.is-dragging {
  opacity: 0.35;
  transform: scale(0.97);
}

.kanban-card.is-saving {
  opacity: 0.65;
  cursor: progress;
}

.k-title {
  margin: 0 0 8px;
  font-size: 13px;
  font-weight: 700;
  color: #17202a;
  line-height: 1.3;
}

.k-sep {
  color: #c0cdd8;
  margin: 0 2px;
}

.k-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 11px;
  color: #8a9bab;
  line-height: 1.4;
}

.k-saving {
  margin: 6px 0 0;
  font-size: 11px;
  color: #ba5c3d;
  font-weight: 600;
}

.lane-empty {
  margin: 20px 0 0;
  color: #c0cdd8;
  font-size: 12px;
  text-align: center;
}

/* ── Responsive ── */
@media (max-width: 1180px) {
  .form-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .kanban-board {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 860px) {
  .personnel-page {
    gap: 18px;
  }

  .page-header h1 {
    font-size: 24px;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .roster-table {
    font-size: 13px;
  }

  .roster-table thead th,
  .roster-table tbody td {
    padding: 8px 10px;
  }

  .header-right {
    align-self: flex-start;
  }

  .kanban-board {
    grid-template-columns: 1fr;
    padding: 0 20px 20px;
  }

  .modal-header {
    padding: 20px;
  }
}
</style>
