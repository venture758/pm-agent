<script setup>
import { computed, onMounted, ref, watch } from "vue";

import { useWorkspaceStore } from "../stores/workspace";

const workspaceStore = useWorkspaceStore();
const activeTab = ref("stories");
const storyOnlyFile = ref(null);
const taskOnlyFile = ref(null);
const taskFilterOwner = ref("");
const taskFilterStatus = ref("");
const taskFilterProject = ref("");

// Tab state
const TABS = [
  { key: "stories", label: "故事管理" },
  { key: "tasks", label: "任务管理" },
];

const STORY_COLUMNS = [
  { key: "sequence_no", label: "序号" },
  { key: "user_story_code", label: "用户故事编码" },
  { key: "user_story_name", label: "用户故事名称" },
  { key: "user_story_tag", label: "用户故事标签" },
  { key: "status", label: "状态" },
  { key: "remark", label: "备注" },
  { key: "plan_test_completion_time", label: "计划提测完成时间" },
  { key: "related_task_count", label: "关联任务" },
  { key: "planned_person_days", label: "计划人天" },
  { key: "owner_names", label: "负责人" },
  { key: "tester_names", label: "测试人员名称" },
  { key: "requirement_owner_names", label: "需求人员名称" },
  { key: "product", label: "产品" },
  { key: "created_time", label: "创建时间" },
  { key: "created_by", label: "创建人" },
  { key: "actual_person_days", label: "实际人天" },
  { key: "planned_dev_person_days", label: "计划开发人天" },
  { key: "related_defect_count", label: "关联缺陷" },
  { key: "version", label: "版本" },
  { key: "priority", label: "优先级" },
  { key: "absolute_priority", label: "绝对优先级" },
  { key: "related_case_count", label: "关联用例" },
  { key: "plan_trunk_test_completion_time", label: "计划主干测试完成时间" },
  { key: "modified_time", label: "修改时间" },
  { key: "acceptance_criteria", label: "验收标准" },
  { key: "detail_url", label: "详细说明（URL）" },
  { key: "project_status", label: "立项状态" },
  { key: "iteration_phase", label: "迭代阶段" },
  { key: "iteration_goal", label: "迭代目标" },
  { key: "release_plan", label: "发布计划" },
  { key: "release_window", label: "发布窗口" },
  { key: "scrum_team", label: "Scrum团队" },
  { key: "product_group", label: "产品组" },
  { key: "project_name", label: "所属项目" },
  { key: "ksm_or_bug_no", label: "KSM或BUG编号" },
  { key: "story_type", label: "类型" },
  { key: "cloud_name", label: "所属云" },
  { key: "application_name", label: "所属应用" },
  { key: "related_story", label: "关联故事" },
  { key: "related_requirement", label: "关联需求" },
  { key: "completed_time", label: "完成时间" },
  { key: "plan_baseline_test_completion_time", label: "计划基线测试完成时间" },
  { key: "developer_names", label: "开发人员名称" },
  { key: "has_upgrade_notice", label: "是否有升级注意事项" },
  { key: "change_type", label: "变动类型" },
];

// Primary (visible by default) and secondary columns for story table
const STORY_PRIMARY_KEYS = new Set([
  "sequence_no", "user_story_code", "user_story_name", "user_story_tag",
  "status", "priority", "planned_person_days", "owner_names",
  "tester_names", "product", "version", "project_name",
]);
const STORY_SECONDARY_COLUMNS = STORY_COLUMNS.filter((c) => !STORY_PRIMARY_KEYS.has(c.key));

const TASK_COLUMNS = [
  { key: "sequence_no", label: "序号" },
  { key: "task_code", label: "任务编号" },
  { key: "related_story", label: "关联用户故事" },
  { key: "name", label: "任务名称" },
  { key: "task_type", label: "任务类型" },
  { key: "owner", label: "负责人" },
  { key: "status", label: "状态" },
  { key: "estimated_start", label: "预计开始时间" },
  { key: "estimated_end", label: "预计结束时间" },
  { key: "completed_time", label: "完成时间" },
  { key: "planned_person_days", label: "计划人天" },
  { key: "actual_person_days", label: "实际人天" },
  { key: "product", label: "产品" },
  { key: "module_path", label: "模块路径" },
  { key: "project_name", label: "所属项目" },
  { key: "version", label: "版本" },
  { key: "iteration_phase", label: "迭代阶段" },
  { key: "project_group", label: "项目组" },
  { key: "participants", label: "参与人" },
  { key: "defect_count", label: "缺陷总数" },
  { key: "created_by", label: "创建人" },
  { key: "created_time", label: "创建时间" },
  { key: "modified_by", label: "修改人" },
  { key: "modified_time", label: "修改时间" },
];

const TASK_PRIMARY_KEYS = new Set([
  "sequence_no", "task_code", "name", "task_type", "owner",
  "status", "planned_person_days", "actual_person_days",
  "project_name", "version", "estimated_end",
]);
const TASK_SECONDARY_COLUMNS = TASK_COLUMNS.filter((c) => !TASK_PRIMARY_KEYS.has(c.key));

// Data
const stories = computed(() => workspaceStore.workspace.handoff.stories || []);
const tasks = computed(() => {
  if (workspaceStore.taskList && workspaceStore.taskList.length > 0) return workspaceStore.taskList;
  return workspaceStore.workspace.handoff.tasks || [];
});

// Story management state
const storySearch = ref("");
const storyPriorityFilter = ref("");
const storySortKey = ref("");
const storySortOrder = ref("asc");
const storyShowAllColumns = ref(false);

function resolveStoryCell(story, key) {
  if (key === "user_story_name") return story.user_story_name || story.name || "";
  if (key === "owner_names") return story.owner_names || story.owner || "";
  if (key === "tester_names") return story.tester_names || story.tester || "";
  if (key === "developer_names") return story.developer_names || (story.developers || []).join(";") || "";
  if (key === "plan_test_completion_time") return story.plan_test_completion_time || story.plan_test_date || "";
  if (key === "related_defect_count") {
    if (story.related_defect_count !== null && story.related_defect_count !== undefined) return story.related_defect_count;
    return story.defects ?? "";
  }
  if (key === "application_name") return story.application_name || story.module_path || "";
  return story[key] ?? "";
}

const storyPriorityOptions = computed(() =>
  [...new Set(stories.value.map((s) => String(resolveStoryCell(s, "priority") || "").trim()).filter(Boolean))].sort(),
);

const activeFilterCount = computed(() => {
  let n = 0;
  if (storyPriorityFilter.value) n++;
  if (storySearch.value.trim()) n++;
  return n;
});

const visibleStories = computed(() => {
  const keyword = storySearch.value.trim().toLowerCase();
  let rows = stories.value.filter((s) => {
    if (storyPriorityFilter.value && String(resolveStoryCell(s, "priority") || "") !== storyPriorityFilter.value) return false;
    if (!keyword) return true;
    return STORY_COLUMNS
      .map((column) => String(resolveStoryCell(s, column.key) || ""))
      .join(" ")
      .toLowerCase()
      .includes(keyword);
  });
  if (storySortKey.value) {
    rows = [...rows].sort((a, b) => {
      const va = String(resolveStoryCell(a, storySortKey.value) || "").toLowerCase();
      const vb = String(resolveStoryCell(b, storySortKey.value) || "").toLowerCase();
      const cmp = va.localeCompare(vb, "zh-Hans-CN");
      return storySortOrder.value === "asc" ? cmp : -cmp;
    });
  }
  return rows;
});

function toggleStorySort(key) {
  if (storySortKey.value === key) {
    storySortOrder.value = storySortOrder.value === "asc" ? "desc" : "asc";
  } else {
    storySortKey.value = key;
    storySortOrder.value = "asc";
  }
}

function sortIndicator(key) {
  if (storySortKey.value !== key) return "";
  return storySortOrder.value === "asc" ? " ↑" : " ↓";
}

function resetStoryFilters() {
  storySearch.value = "";
  storyPriorityFilter.value = "";
  storySortKey.value = "";
  storySortOrder.value = "asc";
}

// Task management state
const taskSearch = ref("");
const taskSortKey = ref("");
const taskSortOrder = ref("asc");
const taskShowAllColumns = ref(false);

const taskOwnerOptions = computed(() =>
  [...new Set(tasks.value.map((t) => String(t.owner || "").trim()).filter(Boolean))].sort(),
);
const taskStatusOptions = computed(() =>
  [...new Set(tasks.value.map((t) => String(t.status || "").trim()).filter(Boolean))].sort(),
);
const taskProjectOptions = computed(() =>
  [...new Set(tasks.value.map((t) => String(t.project_name || "").trim()).filter(Boolean))].sort(),
);

function resolveTaskCell(task, key) {
  if (key === "participants") {
    const p = task.participants;
    if (Array.isArray(p)) return p.join("; ");
    return String(p || "");
  }
  return task[key] ?? "";
}

const taskActiveFilterCount = computed(() => {
  let n = 0;
  if (taskFilterOwner.value) n++;
  if (taskFilterStatus.value) n++;
  if (taskFilterProject.value) n++;
  if (taskSearch.value.trim()) n++;
  return n;
});

const visibleTasks = computed(() => {
  const keyword = taskSearch.value.trim().toLowerCase();
  let rows = tasks.value.filter((t) => {
    if (taskFilterOwner.value && String(t.owner || "") !== taskFilterOwner.value) return false;
    if (taskFilterStatus.value && String(t.status || "") !== taskFilterStatus.value) return false;
    if (taskFilterProject.value && String(t.project_name || "") !== taskFilterProject.value) return false;
    if (!keyword) return true;
    return TASK_COLUMNS
      .map((column) => String(resolveTaskCell(t, column.key) || ""))
      .join(" ")
      .toLowerCase()
      .includes(keyword);
  });
  if (taskSortKey.value) {
    rows = [...rows].sort((a, b) => {
      const va = String(resolveTaskCell(a, taskSortKey.value) || "").toLowerCase();
      const vb = String(resolveTaskCell(b, taskSortKey.value) || "").toLowerCase();
      const cmp = va.localeCompare(vb, "zh-Hans-CN");
      return taskSortOrder.value === "asc" ? cmp : -cmp;
    });
  }
  return rows;
});

function toggleTaskSort(key) {
  if (taskSortKey.value === key) {
    taskSortOrder.value = taskSortOrder.value === "asc" ? "desc" : "asc";
  } else {
    taskSortKey.value = key;
    taskSortOrder.value = "asc";
  }
}

function taskSortIndicator(key) {
  if (taskSortKey.value !== key) return "";
  return taskSortOrder.value === "asc" ? " ↑" : " ↓";
}

async function applyTaskFilters() {
  await workspaceStore.loadTasks({
    owner: taskFilterOwner.value || undefined,
    status: taskFilterStatus.value || undefined,
    project_name: taskFilterProject.value || undefined,
  });
}

function resetTaskFilters() {
  taskFilterOwner.value = "";
  taskFilterStatus.value = "";
  taskFilterProject.value = "";
  taskSearch.value = "";
  workspaceStore.loadTasks();
}

function fileStatus(file, label) {
  if (!file) return { text: `待上传 ${label}`, status: "empty" };
  return { text: file.name, status: "ready" };
}

const storyOnlyStatus = computed(() => fileStatus(storyOnlyFile.value, "故事列表"));
const taskOnlyStatus = computed(() => fileStatus(taskOnlyFile.value, "任务列表"));
const latestStoryImport = computed(() => workspaceStore.workspace.latest_story_import || null);
const latestTaskImport = computed(() => workspaceStore.workspace.latest_task_import || null);
const storyImportErrorsPreview = computed(() => (latestStoryImport.value?.errors || []).slice(0, 5));
const taskImportErrorsPreview = computed(() => (latestTaskImport.value?.errors || []).slice(0, 5));

async function importStoryOnly() {
  if (!storyOnlyFile.value) return;
  await workspaceStore.uploadStoryOnly(storyOnlyFile.value);
  storyOnlyFile.value = null;
}

async function importTaskOnly() {
  if (!taskOnlyFile.value) return;
  await workspaceStore.uploadTaskOnly(taskOnlyFile.value);
  await workspaceStore.loadTasks();
  taskOnlyFile.value = null;
}

watch(activeTab, (tab) => {
  if (tab === "tasks") {
    workspaceStore.loadTasks();
  }
});

onMounted(() => {
  workspaceStore.loadTasks();
});
</script>

<template>
  <section class="delivery-page">
    <!-- Tab bar -->
    <nav class="tab-bar">
      <button
        v-for="tab in TABS"
        :key="tab.key"
        class="tab-item"
        :class="{ 'tab-item--active': activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        <span>{{ tab.label }}</span>
        <span v-if="tab.key === 'stories'" class="tab-badge">{{ stories.length }}</span>
        <span v-else-if="tab.key === 'tasks'" class="tab-badge">{{ tasks.length }}</span>
      </button>
    </nav>

    <!-- Tab 1: Story Management -->
    <div v-show="activeTab === 'stories'" class="tab-panel">
      <!-- ====== Command Strip: Search + Filters ====== -->
      <div class="command-strip">
        <div class="strip-search">
          <svg class="strip-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            v-model="storySearch"
            type="text"
            class="strip-input"
            placeholder="搜索故事编码、名称、负责人…"
          />
          <kbd v-if="!storySearch" class="strip-kbd">⌘K</kbd>
        </div>

        <div class="strip-chips">
          <!-- Priority filter chip -->
          <div class="chip-dropdown">
            <button class="chip-btn" :class="{ 'chip-btn--active': storyPriorityFilter }">
              <span class="chip-label">优先级</span>
              <span class="chip-value">{{ storyPriorityFilter || '全部' }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': !storyPriorityFilter }" @click="storyPriorityFilter = ''">全部</button>
              <button
                v-for="p in storyPriorityOptions"
                :key="p"
                class="chip-menu-item"
                :class="{ 'chip-menu-item--active': storyPriorityFilter === p }"
                @click="storyPriorityFilter = p"
              >
                {{ p }}
              </button>
            </div>
          </div>

          <!-- Active filter badges -->
          <span v-if="storyPriorityFilter" class="filter-badge">
            {{ storyPriorityFilter }}
            <button class="filter-badge-x" @click="storyPriorityFilter = ''">×</button>
          </span>

          <!-- Reset -->
          <button
            v-if="activeFilterCount > 0"
            class="strip-reset"
            @click="resetStoryFilters"
          >
            清除筛选
          </button>

          <!-- Column toggle -->
          <button class="strip-cols" @click="storyShowAllColumns = !storyShowAllColumns" :title="storyShowAllColumns ? '精简列' : '展开全部列'">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
            </svg>
            <span>{{ storyShowAllColumns ? '精简' : '全列' }}</span>
          </button>
        </div>
      </div>

      <!-- ====== Import Feed ====== -->
      <div class="import-feed">
        <label class="feed-drop" :class="`feed-drop--${storyOnlyStatus.status}`">
          <div class="feed-drop-inner">
            <div class="feed-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div class="feed-text">
              <strong>{{ storyOnlyFile ? storyOnlyFile.name : '拖拽或点击上传故事 Excel' }}</strong>
              <span class="feed-hint">{{ storyOnlyStatus.text }}</span>
            </div>
          </div>
          <input type="file" accept=".xlsx,.xls" @change="storyOnlyFile = $event.target.files[0]" />
        </label>
        <button
          class="feed-go"
          :class="{ 'feed-go--active': storyOnlyFile && !workspaceStore.loading }"
          :disabled="!storyOnlyFile || workspaceStore.loading"
          @click="importStoryOnly"
        >
          {{ workspaceStore.loading ? '导入中…' : '导入' }}
        </button>
      </div>

      <!-- Import result summary -->
      <div v-if="latestStoryImport" class="import-result">
        <div class="import-stats">
          <span class="stat stat--total">总计 {{ latestStoryImport.total ?? 0 }}</span>
          <span class="stat stat--ok">新增 {{ latestStoryImport.created ?? 0 }}</span>
          <span class="stat stat--ok">更新 {{ latestStoryImport.updated ?? 0 }}</span>
          <span v-if="(latestStoryImport.failed ?? 0) > 0" class="stat stat--err">失败 {{ latestStoryImport.failed ?? 0 }}</span>
        </div>
        <div v-if="storyImportErrorsPreview.length" class="import-errors">
          <p v-for="item in storyImportErrorsPreview" :key="`${item.row}-${item.reason}`">第 {{ item.row }} 行：{{ item.reason }}</p>
        </div>
      </div>

      <!-- ====== Data Table ====== -->
      <div class="table-frame">
        <div class="table-head-bar">
          <span class="table-count">{{ visibleStories.length }} / {{ stories.length }} 条</span>
        </div>
        <div v-if="visibleStories.length" class="table-wrap">
          <table class="data-tbl story-tbl">
            <thead>
              <tr>
                <th
                  v-for="column in STORY_COLUMNS"
                  :key="column.key"
                  class="tbl-head"
                  :class="{ 'tbl-head--sorted': storySortKey === column.key, 'tbl-head--secondary': storyShowAllColumns ? false : !STORY_PRIMARY_KEYS.has(column.key) }"
                  @click="toggleStorySort(column.key)"
                >
                  {{ column.label }}<span class="sort-mark">{{ sortIndicator(column.key) }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="story in visibleStories" :key="story.user_story_code">
                <td
                  v-for="column in STORY_COLUMNS"
                  :key="column.key"
                  class="tbl-cell"
                  :class="{ 'tbl-cell--code': column.key === 'user_story_code', 'tbl-cell--secondary': storyShowAllColumns ? false : !STORY_PRIMARY_KEYS.has(column.key) }"
                >
                  {{ resolveStoryCell(story, column.key) || "—" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state compact">
          <svg viewBox="0 0 64 64" width="40" height="40" fill="none" stroke="#8a9bab" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="10" y="6" width="44" height="52" rx="4" />
            <path d="M20 20h24M20 30h24M20 40h16" />
          </svg>
          <p>{{ stories.length ? "当前筛选条件下无数据" : "暂无故事数据，请先上传故事列表 Excel" }}</p>
        </div>
      </div>
    </div>

    <!-- Tab 2: Task Management -->
    <div v-show="activeTab === 'tasks'" class="tab-panel">
      <!-- ====== Command Strip: Search + Filters ====== -->
      <div class="command-strip">
        <div class="strip-search">
          <svg class="strip-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
          <input
            v-model="taskSearch"
            type="text"
            class="strip-input"
            placeholder="搜索任务编号、名称、负责人…"
          />
        </div>

        <div class="strip-chips">
          <!-- Owner filter chip -->
          <div class="chip-dropdown">
            <button class="chip-btn" :class="{ 'chip-btn--active': taskFilterOwner }">
              <span class="chip-label">负责人</span>
              <span class="chip-value">{{ taskFilterOwner || '全部' }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': !taskFilterOwner }" @click="taskFilterOwner = ''">全部</button>
              <button
                v-for="o in taskOwnerOptions"
                :key="o"
                class="chip-menu-item"
                :class="{ 'chip-menu-item--active': taskFilterOwner === o }"
                @click="taskFilterOwner = o; applyTaskFilters()"
              >
                {{ o }}
              </button>
            </div>
          </div>

          <!-- Status filter chip -->
          <div class="chip-dropdown">
            <button class="chip-btn" :class="{ 'chip-btn--active': taskFilterStatus }">
              <span class="chip-label">状态</span>
              <span class="chip-value">{{ taskFilterStatus || '全部' }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': !taskFilterStatus }" @click="taskFilterStatus = ''">全部</button>
              <button
                v-for="s in taskStatusOptions"
                :key="s"
                class="chip-menu-item"
                :class="{ 'chip-menu-item--active': taskFilterStatus === s }"
                @click="taskFilterStatus = s; applyTaskFilters()"
              >
                {{ s }}
              </button>
            </div>
          </div>

          <!-- Project filter chip -->
          <div class="chip-dropdown">
            <button class="chip-btn" :class="{ 'chip-btn--active': taskFilterProject }">
              <span class="chip-label">项目</span>
              <span class="chip-value">{{ taskFilterProject || '全部' }}</span>
              <svg class="chip-arrow" viewBox="0 0 12 8" width="12" height="8"><path d="M1 1l5 5 5-5" stroke="currentColor" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>
            </button>
            <div class="chip-menu">
              <button class="chip-menu-item" :class="{ 'chip-menu-item--active': !taskFilterProject }" @click="taskFilterProject = ''">全部</button>
              <button
                v-for="p in taskProjectOptions"
                :key="p"
                class="chip-menu-item"
                :class="{ 'chip-menu-item--active': taskFilterProject === p }"
                @click="taskFilterProject = p; applyTaskFilters()"
              >
                {{ p }}
              </button>
            </div>
          </div>

          <!-- Active filter badges -->
          <span v-if="taskFilterOwner" class="filter-badge">
            {{ taskFilterOwner }}
            <button class="filter-badge-x" @click="taskFilterOwner = ''; applyTaskFilters()">×</button>
          </span>
          <span v-if="taskFilterStatus" class="filter-badge">
            {{ taskFilterStatus }}
            <button class="filter-badge-x" @click="taskFilterStatus = ''; applyTaskFilters()">×</button>
          </span>
          <span v-if="taskFilterProject" class="filter-badge">
            {{ taskFilterProject }}
            <button class="filter-badge-x" @click="taskFilterProject = ''; applyTaskFilters()">×</button>
          </span>

          <!-- Reset -->
          <button
            v-if="taskActiveFilterCount > 0"
            class="strip-reset"
            @click="resetTaskFilters"
          >
            清除筛选
          </button>

          <!-- Column toggle -->
          <button class="strip-cols" @click="taskShowAllColumns = !taskShowAllColumns" :title="taskShowAllColumns ? '精简列' : '展开全部列'">
            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
              <rect x="3" y="3" width="7" height="7" />
              <rect x="14" y="3" width="7" height="7" />
              <rect x="3" y="14" width="7" height="7" />
              <rect x="14" y="14" width="7" height="7" />
            </svg>
            <span>{{ taskShowAllColumns ? '精简' : '全列' }}</span>
          </button>
        </div>
      </div>

      <!-- ====== Import Feed ====== -->
      <div class="import-feed">
        <label class="feed-drop" :class="`feed-drop--${taskOnlyStatus.status}`">
          <div class="feed-drop-inner">
            <div class="feed-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="17 8 12 3 7 8" />
                <line x1="12" y1="3" x2="12" y2="15" />
              </svg>
            </div>
            <div class="feed-text">
              <strong>{{ taskOnlyFile ? taskOnlyFile.name : '拖拽或点击上传任务 Excel' }}</strong>
              <span class="feed-hint">{{ taskOnlyStatus.text }}</span>
            </div>
          </div>
          <input type="file" accept=".xlsx,.xls" @change="taskOnlyFile = $event.target.files[0]" />
        </label>
        <button
          class="feed-go"
          :class="{ 'feed-go--active': taskOnlyFile && !workspaceStore.loading }"
          :disabled="!taskOnlyFile || workspaceStore.loading"
          @click="importTaskOnly"
        >
          {{ workspaceStore.loading ? '导入中…' : '导入' }}
        </button>
      </div>

      <!-- Import result summary -->
      <div v-if="latestTaskImport" class="import-result">
        <div class="import-stats">
          <span class="stat stat--total">总计 {{ latestTaskImport.total ?? 0 }}</span>
          <span class="stat stat--ok">新增 {{ latestTaskImport.created ?? 0 }}</span>
          <span class="stat stat--ok">更新 {{ latestTaskImport.updated ?? 0 }}</span>
          <span v-if="(latestTaskImport.failed ?? 0) > 0" class="stat stat--err">失败 {{ latestTaskImport.failed ?? 0 }}</span>
        </div>
        <div v-if="taskImportErrorsPreview.length" class="import-errors">
          <p v-for="item in taskImportErrorsPreview" :key="`${item.row}-${item.reason}`">第 {{ item.row }} 行：{{ item.reason }}</p>
        </div>
      </div>

      <!-- ====== Data Table ====== -->
      <div class="table-frame">
        <div class="table-head-bar">
          <span class="table-count">{{ visibleTasks.length }} / {{ tasks.length }} 条</span>
        </div>
        <div v-if="visibleTasks.length" class="table-wrap">
          <table class="data-tbl task-tbl">
            <thead>
              <tr>
                <th
                  v-for="column in TASK_COLUMNS"
                  :key="column.key"
                  class="tbl-head"
                  :class="{ 'tbl-head--sorted': taskSortKey === column.key, 'tbl-head--secondary': taskShowAllColumns ? false : !TASK_PRIMARY_KEYS.has(column.key) }"
                  @click="toggleTaskSort(column.key)"
                >
                  {{ column.label }}<span class="sort-mark">{{ taskSortIndicator(column.key) }}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="task in visibleTasks" :key="task.task_code">
                <td
                  v-for="column in TASK_COLUMNS"
                  :key="column.key"
                  class="tbl-cell"
                  :class="{ 'tbl-cell--code': column.key === 'task_code', 'tbl-cell--secondary': taskShowAllColumns ? false : !TASK_PRIMARY_KEYS.has(column.key) }"
                >
                  {{ resolveTaskCell(task, column.key) || "—" }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="empty-state compact">
          <svg viewBox="0 0 64 64" width="40" height="40" fill="none" stroke="#8a9bab" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <rect x="10" y="6" width="44" height="52" rx="4" />
            <path d="M20 20h24M20 30h24M20 40h16" />
          </svg>
          <p>{{ tasks.length ? "当前筛选条件下无数据" : "暂无任务数据，请先上传任务列表 Excel" }}</p>
        </div>
      </div>
    </div>
  </section>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Source+Sans+3:wght@400;600;700&display=swap');

.delivery-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  animation: pageFadeIn 0.35s ease both;
}

@keyframes pageFadeIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

/* ====== Tab bar ====== */
.tab-bar {
  display: inline-flex;
  gap: 2px;
  padding: 3px;
  background: #1a2636;
  border-radius: 12px;
  align-self: flex-start;
}

.tab-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: rgba(244, 241, 235, 0.5);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  white-space: nowrap;
}

.tab-item:hover:not(.tab-item--active) {
  color: rgba(244, 241, 235, 0.8);
}

.tab-item--active {
  background: #ba5c3d;
  color: #fff;
  box-shadow: 0 2px 8px rgba(186, 92, 61, 0.3);
}

.tab-badge {
  font-size: 11px;
  padding: 1px 7px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  color: rgba(244, 241, 235, 0.5);
  font-weight: 700;
  line-height: 1.4;
}

.tab-item--active .tab-badge {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
}

/* ====== Command Strip ====== */
.command-strip {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  background: #1a2636;
  border-radius: 14px;
  padding: 8px 14px;
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.strip-search {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
  min-width: 200px;
  position: relative;
}

.strip-icon {
  color: rgba(244, 241, 235, 0.35);
  flex-shrink: 0;
}

.strip-input {
  width: 100%;
  border: none;
  background: transparent;
  color: #f4f1eb;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 14px;
  padding: 6px 0;
  outline: none;
}

.strip-input::placeholder {
  color: rgba(244, 241, 235, 0.3);
}

.strip-kbd {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  font-size: 10px;
  font-family: 'Source Sans 3', monospace;
  color: rgba(244, 241, 235, 0.2);
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 4px;
  padding: 2px 5px;
  pointer-events: none;
}

.strip-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

/* Chip button (dropdown trigger) */
.chip-dropdown {
  position: relative;
}

.chip-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 12px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.04);
  color: rgba(244, 241, 235, 0.6);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.chip-btn:hover {
  background: rgba(255, 255, 255, 0.08);
  border-color: rgba(255, 255, 255, 0.15);
}

.chip-btn--active {
  background: rgba(186, 92, 61, 0.2);
  border-color: rgba(186, 92, 61, 0.35);
  color: #e4a882;
}

.chip-label {
  opacity: 0.6;
}

.chip-value {
  max-width: 80px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chip-arrow {
  opacity: 0.4;
  flex-shrink: 0;
}

/* Dropdown menu */
.chip-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 10;
  min-width: 160px;
  max-height: 240px;
  overflow-y: auto;
  background: #1e3040;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 10px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.3);
  padding: 4px;
  display: none;
}

.chip-dropdown:hover .chip-menu {
  display: block;
}

.chip-menu-item {
  display: block;
  width: 100%;
  text-align: left;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: rgba(244, 241, 235, 0.7);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 600;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.12s ease;
}

.chip-menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.chip-menu-item--active {
  background: rgba(186, 92, 61, 0.2);
  color: #e4a882;
}

/* Filter badge */
.filter-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 6px;
  background: rgba(228, 189, 121, 0.15);
  color: #e4bd79;
  font-size: 11px;
  font-weight: 700;
}

.filter-badge-x {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: #e4bd79;
  font-size: 14px;
  cursor: pointer;
  padding: 0 2px;
  opacity: 0.7;
  line-height: 1;
}

.filter-badge-x:hover {
  opacity: 1;
}

/* Reset button */
.strip-reset {
  padding: 5px 10px;
  border: 1px dashed rgba(244, 241, 235, 0.15);
  border-radius: 8px;
  background: transparent;
  color: rgba(244, 241, 235, 0.4);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.strip-reset:hover {
  background: rgba(255, 255, 255, 0.06);
  color: rgba(244, 241, 235, 0.7);
  border-color: rgba(244, 241, 235, 0.25);
}

/* Column toggle */
.strip-cols {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.03);
  color: rgba(244, 241, 235, 0.45);
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 11px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s ease;
}

.strip-cols:hover {
  background: rgba(255, 255, 255, 0.08);
  color: rgba(244, 241, 235, 0.7);
}

/* ====== Import Feed ====== */
.import-feed {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 10px;
  align-items: center;
}

.feed-drop {
  position: relative;
  display: flex;
  flex-direction: column;
  justify-content: center;
  padding: 14px 20px;
  border: 1.5px dashed rgba(23, 32, 42, 0.12);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.6);
  cursor: pointer;
  transition: all 0.2s ease;
  overflow: hidden;
}

.feed-drop::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: #c6d0dc;
  border-radius: 0 2px 2px 0;
  transition: background 0.2s ease;
}

.feed-drop:hover {
  border-color: #ba5c3d;
  background: rgba(255, 248, 235, 0.5);
}

.feed-drop:hover::before {
  background: #ba5c3d;
}

.feed-drop--ready {
  border-color: #3a8a5c;
  border-style: solid;
  background: rgba(58, 138, 92, 0.03);
}

.feed-drop--ready::before {
  background: #3a8a5c;
}

.feed-drop input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

.feed-drop-inner {
  display: flex;
  align-items: center;
  gap: 14px;
}

.feed-icon {
  color: #8a9bab;
  flex-shrink: 0;
  transition: color 0.2s ease;
}

.feed-drop--ready .feed-icon {
  color: #3a8a5c;
}

.feed-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.feed-text strong {
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: #17202a;
}

.feed-hint {
  font-size: 12px;
  color: #8a9bab;
}

.feed-go {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 12px 32px;
  border: none;
  border-radius: 10px;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  background: #d2dbe5;
  color: rgba(255, 255, 255, 0.4);
  transition: all 0.2s ease;
  min-width: 90px;
}

.feed-go--active {
  background: #ba5c3d;
  color: #fff;
  box-shadow: 0 4px 14px rgba(186, 92, 61, 0.2);
}

.feed-go--active:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 8px 20px rgba(186, 92, 61, 0.25);
}

/* ====== Import Result ====== */
.import-result {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 14px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.5);
  border: 1px solid #e8edf3;
}

.import-stats {
  display: flex;
  gap: 14px;
  flex-wrap: wrap;
}

.stat {
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 700;
  padding: 3px 10px;
  border-radius: 6px;
}

.stat--total {
  background: rgba(33, 58, 79, 0.08);
  color: #213a4f;
}

.stat--ok {
  background: rgba(58, 138, 92, 0.1);
  color: #2a6b48;
}

.stat--err {
  background: rgba(138, 31, 40, 0.1);
  color: #8a1f28;
}

.import-errors {
  font-size: 12px;
  color: #8c2f2f;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.import-errors p {
  margin: 0;
}

/* ====== Table Frame ====== */
.table-frame {
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(23, 32, 42, 0.08);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 16px rgba(28, 46, 64, 0.04);
}

.table-head-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 14px;
  background: rgba(250, 251, 252, 0.8);
  border-bottom: 1px solid #eef1f5;
}

.table-count {
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 12px;
  font-weight: 700;
  color: #627284;
  letter-spacing: 0.02em;
}

.table-wrap {
  overflow: auto;
}

/* ====== Data Table ====== */
.data-tbl {
  width: 100%;
  border-collapse: collapse;
}

.story-tbl {
  min-width: 1800px;
}

.task-tbl {
  min-width: 1600px;
}

.data-tbl thead th {
  position: sticky;
  top: 0;
  z-index: 2;
}

.tbl-head {
  padding: 9px 12px;
  text-align: left;
  border-bottom: 2px solid #eef1f5;
  background: #fafbfc;
  color: #627284;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  cursor: pointer;
  user-select: none;
  transition: color 0.15s ease, background 0.15s ease;
  white-space: nowrap;
}

.tbl-head:hover {
  color: #ba5c3d;
  background: #f5f7fa;
}

.tbl-head--sorted {
  color: #ba5c3d;
  background: rgba(186, 92, 61, 0.04);
  border-bottom-color: rgba(186, 92, 61, 0.2);
}

/* Secondary columns are hidden by default */
.tbl-head--secondary {
  display: none;
}

.sort-mark {
  font-size: 10px;
  margin-left: 2px;
  opacity: 0.5;
}

.data-tbl tbody tr {
  transition: background 0.12s ease;
}

.data-tbl tbody tr:hover {
  background: rgba(255, 248, 235, 0.3);
}

.tbl-cell {
  padding: 8px 12px;
  border-bottom: 1px solid #f3f5f8;
  font-family: 'Source Sans 3', 'PingFang SC', sans-serif;
  font-size: 13px;
  color: #17202a;
  white-space: nowrap;
  vertical-align: middle;
}

.data-tbl tbody tr:last-child .tbl-cell {
  border-bottom: none;
}

.tbl-cell--code {
  font-family: 'SF Mono', 'Menlo', monospace;
  font-size: 12px;
  color: #4b5b6b;
}

/* Secondary columns hidden in body too */
.tbl-cell--secondary {
  display: none;
}

/* ====== Empty state ====== */
.empty-state {
  width: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 20px;
  color: #8a9bab;
  text-align: center;
  font-size: 14px;
}

.empty-state.compact {
  padding: 36px 20px;
}

/* ====== Responsive ====== */
@media (max-width: 860px) {
  .command-strip {
    flex-direction: column;
    align-items: stretch;
  }

  .strip-chips {
    justify-content: flex-start;
  }

  .import-feed {
    grid-template-columns: 1fr;
  }

  .feed-go {
    align-self: flex-end;
  }

  .tab-bar {
    align-self: stretch;
  }

  .tab-item {
    flex: 1;
    justify-content: center;
  }
}
</style>
