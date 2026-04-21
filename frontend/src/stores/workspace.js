import { defineStore } from "pinia";

import { apiClient } from "../api/client";

const PIPELINE_POLL_INTERVAL_MS = 2000;
let pipelinePollTimer = null;

const PIPELINE_STEPS = [
  "requirement_parsing",
  "personnel_matching",
  "module_extraction",
  "team_analysis",
  "knowledge_update",
];

const PIPELINE_STEP_LABELS = {
  requirement_parsing: "需求解析",
  personnel_matching: "人员匹配",
  module_extraction: "模块提炼",
  team_analysis: "梯队分析",
  knowledge_update: "知识更新",
};

const EMPTY_WORKSPACE = () => ({
  workspace_id: "default",
  title: "default",
  updated_at: "",
  draft: {
    draft_mode: "chat",
    message_text: "",
    requirement_rows: [],
    team_rows: [],
    chat_messages: [],
  },
  requirements: [],
  members: [],
  managed_members: [],
  module_entries: [],
  module_page: {
    page: 1,
    page_size: 50,
    total: 0,
    total_pages: 1,
    filters: {
      big_module: "",
      function_module: "",
      primary_owner: "",
    },
  },
  recommendations: [],
  confirmed_assignments: [],
  handoff: {
    stories: [],
    tasks: [],
  },
  latest_sync_batch: null,
  latest_story_import: null,
  latest_task_import: null,
  uploads: [],
  messages: [],
  knowledge_base_summary: {
    entry_count: 0,
    sample_keys: [],
  },
  latest_knowledge_update: null,
  group_reply_preview: "",
  active_session_id: "",
  session_list: [],
});

function asArray(value) {
  return Array.isArray(value) ? value : [];
}

function toPositiveInt(value, fallback) {
  const n = Number(value);
  if (!Number.isFinite(n) || n <= 0) {
    return fallback;
  }
  return Math.floor(n);
}

function toTotalPages(total, pageSize) {
  const totalValue = Number(total);
  const pageSizeValue = Number(pageSize);
  if (!Number.isFinite(totalValue) || totalValue <= 0 || !Number.isFinite(pageSizeValue) || pageSizeValue <= 0) {
    return 0;
  }
  return Math.ceil(totalValue / pageSizeValue);
}

function normalizeRecommendation(item = {}) {
  return {
    requirement_id: item.requirement_id || "",
    title: item.title || "",
    module_name: item.module_name || "",
    development_owner: item.development_owner || item.developer || "",
    testing_owner: item.testing_owner || item.tester || "",
    backup_owner: item.backup_owner || "",
    collaborators: asArray(item.collaborators),
    confidence: Number(item.confidence ?? 0),
    reason: item.reason || "",
    split_suggestion: item.split_suggestion || "",
    unassigned_reason: item.unassigned_reason || "",
  };
}

function inferRequirementsFromMessages(messages) {
  const dedup = new Map();
  asArray(messages).forEach((message) => {
    asArray(message.parsed_requirements).forEach((item) => {
      const requirementId = String(item.requirement_id || "").trim();
      if (!requirementId) {
        return;
      }
      dedup.set(requirementId, item);
    });
  });
  return [...dedup.values()];
}

function mapPipelineStepStatus(rawStatus) {
  if (rawStatus === "completed" || rawStatus === "skipped") {
    return "completed";
  }
  if (rawStatus === "in_progress" || rawStatus === "awaiting_confirmation") {
    return "current";
  }
  return "pending";
}

function getLastStepWithResult(stepResults = {}) {
  for (let index = PIPELINE_STEPS.length - 1; index >= 0; index -= 1) {
    const step = PIPELINE_STEPS[index];
    if (stepResults[step]) {
      return step;
    }
  }
  return "";
}

function shouldPollPipeline(state) {
  return Boolean(
    state
      && state.execution_mode === "auto"
      && (state.run_status === "queued" || state.run_status === "running"),
  );
}

function stopPipelinePolling() {
  if (pipelinePollTimer) {
    clearInterval(pipelinePollTimer);
    pipelinePollTimer = null;
  }
}

function normalizePipelineState(payload) {
  if (!payload || typeof payload !== "object") {
    return null;
  }
  if (payload.status === "idle" || payload.status === "none") {
    return null;
  }

  const progressMap = payload.step_progress && typeof payload.step_progress === "object"
    ? payload.step_progress
    : {};
  const stepResults = payload.step_results && typeof payload.step_results === "object"
    ? payload.step_results
    : {};
  const currentStep = String(payload.current_step || "");
  const runStatus = String(payload.run_status || payload.status || "running");
  const executionMode = String(payload.execution_mode || "manual");
  const normalizedStatus = runStatus === "completed" ? "complete" : runStatus;
  const displayStep = currentStep || getLastStepWithResult(stepResults);

  const stepProgress = PIPELINE_STEPS.map((step) => ({
    step,
    label: PIPELINE_STEP_LABELS[step] || step,
    status: mapPipelineStepStatus(progressMap[step]),
  }));

  let currentStepIndex = PIPELINE_STEPS.indexOf(currentStep);
  if (currentStepIndex < 0) {
    currentStepIndex = -1;
    for (let i = stepProgress.length - 1; i >= 0; i -= 1) {
      if (stepProgress[i].status === "completed") {
        currentStepIndex = i;
        break;
      }
    }
    if (currentStepIndex < 0) {
      currentStepIndex = 0;
    }
  }

  const requirementResult = stepResults.requirement_parsing || {};
  const matchResult = stepResults.personnel_matching || {};
  const moduleResult = stepResults.module_extraction || {};
  const teamResult = stepResults.team_analysis || {};
  const knowledgeResult = stepResults.knowledge_update || {};
  const displayResult = displayStep ? (stepResults[displayStep] || {}) : {};
  const isComplete = normalizedStatus === "complete";
  const isAwaitingConfirmation = Boolean(payload.awaiting_confirmation) || runStatus === "awaiting_confirmation";

  return {
    ...payload,
    execution_mode: executionMode,
    run_status: runStatus,
    status: normalizedStatus,
    is_complete: isComplete,
    awaiting_confirmation: isAwaitingConfirmation,
    blocking_reason: String(payload.blocking_reason || ""),
    current_step: currentStep,
    current_step_index: currentStepIndex,
    step_progress: stepProgress,
    step_results: stepResults,
    requirements: asArray(requirementResult.requirements || requirementResult.items),
    assignment_suggestions: asArray(matchResult.assignment_suggestions || matchResult.items),
    module_changes: asArray(moduleResult.module_changes || moduleResult.items),
    team_analysis: teamResult,
    pending_changes: asArray(knowledgeResult.pending_changes || knowledgeResult.items),
    display_step: displayStep,
    reply: String(displayResult.summary || payload.reply || ""),
  };
}

function normalizeConfirmationItem(item = {}) {
  const assignments = asArray(item.confirmed_assignments || item.payload).map(normalizeRecommendation);
  return {
    session_id: item.session_id || "",
    confirmed_count: Number(item.confirmed_count || assignments.length),
    created_at: item.created_at || "",
    confirmed_assignments: assignments,
    knowledge_update: {
      status: "skipped",
      has_module_diff_records: false,
      reply: "当前会话未执行知识更新分析。",
    },
  };
}

export const useWorkspaceStore = defineStore("workspace", {
  state: () => ({
    workspaceId: "default",
    workspace: EMPTY_WORKSPACE(),
    moduleQuery: {
      page: 1,
      page_size: 50,
      big_module: "",
      function_module: "",
      primary_owner: "",
    },
    monitoring: [],
    taskList: [],
    insights: {
      heatmap: [],
      single_points: [],
      growth_suggestions: [],
    },
    insightHistory: [],
    insightSummary: null,
    confirmationHistory: {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
      total_pages: 0,
    },
    knowledgeUpdateModuleDiffs: {},
    chatSessions: [],
    activeSessionId: "",
    session_list: [],
    storyPagination: {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
      total_pages: 0,
      keyword: "",
    },
    taskPagination: {
      items: [],
      page: 1,
      page_size: 20,
      total: 0,
      total_pages: 0,
    },
    loading: false,
    error: "",
    pipelineState: null,
  }),
  actions: {
    applyWorkspace(payload = {}) {
      if (!payload || typeof payload !== "object" || Array.isArray(payload)) {
        return;
      }
      const nextWorkspace = {
        ...this.workspace,
        ...payload,
        draft: {
          ...this.workspace.draft,
          ...(payload.draft || {}),
        },
      };
      this.workspace = nextWorkspace;
      this.workspaceId = payload.workspace_id || this.workspaceId;
      this.activeSessionId = payload.active_session_id || this.activeSessionId;
      this.session_list = payload.session_list || this.session_list;
      this.workspace.active_session_id = this.activeSessionId;
      this.workspace.session_list = this.session_list;

      const modulePage = payload.module_page || this.workspace.module_page || {};
      const filters = modulePage.filters || {};
      this.moduleQuery = {
        page: toPositiveInt(modulePage.page, this.moduleQuery.page || 1),
        page_size: toPositiveInt(modulePage.page_size, this.moduleQuery.page_size || 50),
        big_module: String(filters.big_module || ""),
        function_module: String(filters.function_module || ""),
        primary_owner: String(filters.primary_owner || ""),
      };
      this.error = "";
    },

    async loadWorkspace(workspaceId = this.workspaceId) {
      this.loading = true;
      try {
        const payload = await apiClient.getWorkspace(workspaceId);
        this.applyWorkspace({
          workspace_id: payload.workspace_id || workspaceId,
          title: payload.title || this.workspace.title,
          updated_at: payload.updated_at || this.workspace.updated_at,
        });
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async saveDraft(payload) {
      this.loading = true;
      try {
        const result = await apiClient.saveDraft(this.workspaceId, payload);
        this.applyWorkspace({
          workspace_id: result.workspace_id || this.workspaceId,
          title: result.title || this.workspace.title,
          updated_at: result.updated_at || this.workspace.updated_at,
          draft: {
            ...this.workspace.draft,
            draft_mode: result.draft_mode || payload?.draft_mode || "chat",
            message_text: result.message_text || payload?.message_text || "",
            requirement_rows: result.requirement_rows || payload?.requirement_rows || [],
            team_rows: result.team_rows || payload?.team_rows || [],
          },
        });
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async refreshModules(query = {}) {
      this.loading = true;
      try {
        const mergedQuery = { ...this.moduleQuery, ...query };
        const normalizedQuery = {
          page: toPositiveInt(mergedQuery.page, 1),
          page_size: toPositiveInt(mergedQuery.page_size, 50),
          big_module: String(mergedQuery.big_module || ""),
          function_module: String(mergedQuery.function_module || ""),
          primary_owner: String(mergedQuery.primary_owner || ""),
        };
        this.moduleQuery = normalizedQuery;

        const payload = await apiClient.getModules(this.workspaceId, normalizedQuery);
        const items = asArray(payload.items).map((item) => ({
          ...item,
          backup_owners: asArray(item.backup_owners),
          familiar_members: asArray(item.familiar_members),
          aware_members: asArray(item.aware_members),
          unfamiliar_members: asArray(item.unfamiliar_members),
        }));
        const pageSize = toPositiveInt(payload.page_size, normalizedQuery.page_size);
        const total = Number(payload.total || 0);
        const totalPages = toTotalPages(total, pageSize);
        this.workspace.module_entries = items;
        this.workspace.module_page = {
          page: toPositiveInt(payload.page, normalizedQuery.page),
          page_size: pageSize,
          total,
          total_pages: totalPages || 1,
          filters: {
            big_module: normalizedQuery.big_module,
            function_module: normalizedQuery.function_module,
            primary_owner: normalizedQuery.primary_owner,
          },
        };
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async createModule(payload) {
      this.loading = true;
      try {
        await apiClient.createModule(this.workspaceId, payload);
        await this.refreshModules({ ...this.moduleQuery, page: 1 });
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async updateModule(moduleKey, payload) {
      this.loading = true;
      try {
        await apiClient.updateModule(this.workspaceId, moduleKey, payload);
        await this.refreshModules(this.moduleQuery);
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async deleteModule(moduleKey) {
      this.loading = true;
      try {
        await apiClient.deleteModule(this.workspaceId, moduleKey);
        const totalPages = Number(this.workspace.module_page?.total_pages || 1);
        const targetPage = Math.min(this.moduleQuery.page || 1, totalPages);
        await this.refreshModules({ ...this.moduleQuery, page: targetPage });
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async refreshMembers() {
      this.loading = true;
      try {
        const members = asArray(await apiClient.getMembers(this.workspaceId));
        this.workspace.managed_members = members;
        this.workspace.members = members;
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async createMember(payload) {
      this.loading = true;
      try {
        await apiClient.createMember(this.workspaceId, payload);
        await this.refreshMembers();
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async updateMember(memberName, payload) {
      this.loading = true;
      try {
        await apiClient.updateMember(this.workspaceId, memberName, payload);
        await this.refreshMembers();
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async deleteMember(memberName) {
      this.loading = true;
      try {
        await apiClient.deleteMember(this.workspaceId, memberName);
        await this.refreshMembers();
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async generateRecommendations() {
      this.loading = true;
      try {
        const payload = await apiClient.generateRecommendations(this.workspaceId);
        this.workspace.recommendations = asArray(payload.recommendations).map(normalizeRecommendation);
        this.workspace.group_reply_preview = payload.group_reply_preview || "";
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async deleteRecommendation(requirementId) {
      this.loading = true;
      try {
        await apiClient.deleteRecommendation(this.workspaceId, requirementId);
        this.workspace.recommendations = asArray(this.workspace.recommendations).filter(
          (item) => item.requirement_id !== requirementId,
        );
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async batchDeleteRecommendations(requirementIds) {
      this.loading = true;
      try {
        const ids = new Set(asArray(requirementIds));
        await apiClient.batchDeleteRecommendations(this.workspaceId, [...ids]);
        this.workspace.recommendations = asArray(this.workspace.recommendations).filter(
          (item) => !ids.has(item.requirement_id),
        );
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async confirmAssignments(actions) {
      this.loading = true;
      try {
        const payload = await apiClient.confirmAssignments(this.workspaceId, actions);
        const confirmed = asArray(payload.confirmed_assignments).map(normalizeRecommendation);
        const acceptedIds = Object.entries(actions || {})
          .filter(([, action]) => String(action?.action || "").toLowerCase() === "accept")
          .map(([requirementId]) => requirementId);
        const acceptedIdSet = new Set(acceptedIds);
        this.workspace.confirmed_assignments = confirmed;
        this.workspace.recommendations = asArray(this.workspace.recommendations).filter(
          (item) => !acceptedIdSet.has(item.requirement_id),
        );
        this.workspace.latest_knowledge_update = {
          status: "skipped",
          has_module_diff_records: false,
          reply: "当前版本未执行知识更新分析。",
        };
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async uploadModuleKnowledge(file) {
      this.loading = true;
      try {
        const payload = await apiClient.uploadModuleKnowledge(this.workspaceId, file);
        this.workspace.knowledge_base_summary = {
          entry_count: Number(payload.imported_count || payload.success_rows || 0),
          sample_keys: asArray(payload.sample_keys),
        };
        this.workspace.uploads = [...asArray(this.workspace.uploads), payload];
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async syncPlatformExports(storyFile, taskFile) {
      this.loading = true;
      try {
        const payload = await apiClient.syncPlatformExports(this.workspaceId, storyFile, taskFile);
        this.workspace.latest_sync_batch = payload;
        this.workspace.uploads = [...asArray(this.workspace.uploads), payload];
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async uploadStoryOnly(storyFile) {
      this.loading = true;
      try {
        const payload = await apiClient.uploadStoryOnly(this.workspaceId, storyFile);
        this.workspace.latest_story_import = payload;
        this.workspace.uploads = [...asArray(this.workspace.uploads), payload];
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async uploadTaskOnly(taskFile) {
      this.loading = true;
      try {
        const payload = await apiClient.uploadTaskOnly(this.workspaceId, taskFile);
        this.workspace.latest_task_import = payload;
        this.workspace.uploads = [...asArray(this.workspace.uploads), payload];
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async loadTasks(query = {}) {
      this.loading = true;
      try {
        const payload = await apiClient.getTasks(this.workspaceId, query);
        const page = toPositiveInt(payload.page, 1);
        const pageSize = toPositiveInt(payload.page_size, 20);
        const total = Number(payload.total || 0);
        this.taskPagination = {
          items: asArray(payload.items),
          page,
          page_size: pageSize,
          total,
          total_pages: toTotalPages(total, pageSize),
        };
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async loadStories(page = 1, keyword = "") {
      this.loading = true;
      try {
        const payload = await apiClient.listStories(
          this.workspaceId,
          page,
          this.storyPagination.page_size,
          keyword || undefined,
        );
        const pageNo = toPositiveInt(payload.page, 1);
        const pageSize = toPositiveInt(payload.page_size, 20);
        const total = Number(payload.total || 0);
        this.storyPagination = {
          items: asArray(payload.items),
          page: pageNo,
          page_size: pageSize,
          total,
          total_pages: toTotalPages(total, pageSize),
          keyword: keyword || "",
        };
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async refreshMonitoring() {
      this.loading = true;
      try {
        const payload = await apiClient.getMonitoring(this.workspaceId);
        this.monitoring = asArray(payload.alerts);
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async refreshInsights() {
      this.loading = true;
      try {
        const payload = await apiClient.getInsights(this.workspaceId);
        this.insights = {
          heatmap: asArray(payload.heatmap),
          single_points: asArray(payload.single_points),
          growth_suggestions: asArray(payload.growth_suggestions),
        };
        this.insightSummary = payload.summary || null;
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async loadInsightHistory() {
      try {
        const payload = await apiClient.getInsightHistory(this.workspaceId);
        this.insightHistory = asArray(payload.items);
      } catch (error) {
        this.error = error.message;
        throw error;
      }
    },

    async loadConfirmationHistory(page = 1) {
      this.loading = true;
      try {
        const payload = await apiClient.listConfirmationRecords(
          this.workspaceId,
          page,
          this.confirmationHistory.page_size,
        );
        const pageNo = toPositiveInt(payload.page, 1);
        const pageSize = toPositiveInt(payload.page_size, 20);
        const total = Number(payload.total || 0);
        this.confirmationHistory = {
          items: asArray(payload.items).map(normalizeConfirmationItem),
          page: pageNo,
          page_size: pageSize,
          total,
          total_pages: toTotalPages(total, pageSize),
        };
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async loadKnowledgeUpdateModuleDiffs(sessionId, requirementId, { force = false } = {}) {
      const cacheKey = `${sessionId}::${requirementId}`;
      const current = this.knowledgeUpdateModuleDiffs[cacheKey];
      if (!force && current?.loaded) {
        return current.items || [];
      }
      this.knowledgeUpdateModuleDiffs = {
        ...this.knowledgeUpdateModuleDiffs,
        [cacheKey]: {
          items: current?.items || [],
          loading: true,
          loaded: false,
        },
      };
      try {
        const payload = await apiClient.getKnowledgeUpdateModuleDiffs(
          this.workspaceId,
          sessionId,
          requirementId,
        );
        this.knowledgeUpdateModuleDiffs = {
          ...this.knowledgeUpdateModuleDiffs,
          [cacheKey]: {
            items: asArray(payload.items),
            loading: false,
            loaded: true,
          },
        };
        this.error = "";
        return asArray(payload.items);
      } catch (error) {
        this.knowledgeUpdateModuleDiffs = {
          ...this.knowledgeUpdateModuleDiffs,
          [cacheKey]: {
            items: current?.items || [],
            loading: false,
            loaded: false,
          },
        };
        this.error = error.message;
        throw error;
      }
    },

    async sendChatMessage(message) {
      this.loading = true;
      try {
        const result = await apiClient.sendChatMessage(this.workspaceId, message, this.activeSessionId || null);
        const messages = asArray(result.messages).map((item) => ({
          ...item,
          parsed_requirements: asArray(item.parsed_requirements),
        }));
        this.activeSessionId = result.session_id || this.activeSessionId;
        this.workspace.active_session_id = this.activeSessionId;
        this.workspace.draft = {
          ...this.workspace.draft,
          chat_messages: messages,
        };
        this.workspace.requirements = inferRequirementsFromMessages(messages);
        await this.loadSessions();
        this.error = "";
        return result;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async createNewSession() {
      this.loading = true;
      try {
        const result = await apiClient.createChatSession(this.workspaceId);
        this.activeSessionId = result.session_id || "";
        this.workspace.active_session_id = this.activeSessionId;
        this.workspace.draft.chat_messages = [];
        this.workspace.requirements = [];
        await this.loadSessions();
        this.error = "";
        return result;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async switchSession(sessionId) {
      this.loading = true;
      try {
        const result = await apiClient.getChatSession(this.workspaceId, sessionId);
        const messages = asArray(result.messages).map((item) => ({
          ...item,
          parsed_requirements: asArray(item.parsed_requirements),
        }));
        this.workspace.draft.chat_messages = messages;
        this.workspace.requirements = inferRequirementsFromMessages(messages);
        this.activeSessionId = sessionId;
        this.workspace.active_session_id = sessionId;
        this.error = "";
        return result;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async loadSessions() {
      try {
        const result = await apiClient.listChatSessions(this.workspaceId);
        this.session_list = asArray(result.sessions);
        this.activeSessionId = result.active_session_id || this.activeSessionId;
        this.workspace.active_session_id = this.activeSessionId;
        this.workspace.session_list = this.session_list;
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      }
    },

    async deleteSession(sessionId) {
      this.loading = true;
      try {
        const result = await apiClient.deleteChatSession(this.workspaceId, sessionId);
        this.activeSessionId = result.active_session_id || "";
        this.workspace.active_session_id = this.activeSessionId;
        const sessionsResult = await apiClient.listChatSessions(this.workspaceId);
        this.session_list = asArray(sessionsResult.sessions);
        if (this.activeSessionId) {
          const active = await apiClient.getChatSession(this.workspaceId, this.activeSessionId);
          this.workspace.draft.chat_messages = asArray(active.messages);
          this.workspace.requirements = inferRequirementsFromMessages(active.messages);
        } else {
          this.workspace.draft.chat_messages = [];
          this.workspace.requirements = [];
        }
        this.error = "";
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    syncPipelinePolling() {
      if (!shouldPollPipeline(this.pipelineState)) {
        stopPipelinePolling();
        return;
      }
      if (pipelinePollTimer) {
        return;
      }
      pipelinePollTimer = setInterval(() => {
        this.loadPipelineState({ background: true }).catch(() => {});
      }, PIPELINE_POLL_INTERVAL_MS);
    },

    async startPipeline(message = "", executionMode = "auto") {
      this.loading = true;
      try {
        const result = await apiClient.startPipeline(this.workspaceId, message, executionMode);
        this.pipelineState = normalizePipelineState(result);
        this.syncPipelinePolling();
        this.error = "";
        return this.pipelineState;
      } catch (error) {
        stopPipelinePolling();
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },

    async loadPipelineState(options = {}) {
      const background = Boolean(options.background);
      if (!background) {
        this.loading = true;
      }
      try {
        const result = await apiClient.getPipelineState(this.workspaceId);
        this.pipelineState = normalizePipelineState(result);
        this.syncPipelinePolling();
        this.error = "";
        return this.pipelineState;
      } catch (error) {
        stopPipelinePolling();
        this.pipelineState = null;
        this.error = background ? this.error : "";
        return null;
      } finally {
        if (!background) {
          this.loading = false;
        }
      }
    },

    async confirmPipelineStep(action, options = {}) {
      this.loading = true;
      try {
        const result = await apiClient.confirmPipelineStep(this.workspaceId, action, options);
        this.pipelineState = normalizePipelineState(result);
        this.syncPipelinePolling();
        this.error = "";
        return this.pipelineState;
      } catch (error) {
        stopPipelinePolling();
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },
  },
  getters: {
    pipelineActive(state) {
      return Boolean(state.pipelineState);
    },
  },
});
