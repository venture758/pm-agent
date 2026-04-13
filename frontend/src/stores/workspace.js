import { defineStore } from "pinia";

import { apiClient } from "../api/client";

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
  uploads: [],
  messages: [],
  knowledge_base_summary: {
    entry_count: 0,
    sample_keys: [],
  },
  group_reply_preview: "",
});

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
    loading: false,
    error: "",
  }),
  actions: {
    applyWorkspace(payload) {
      this.workspace = {
        ...EMPTY_WORKSPACE(),
        ...payload,
      };
      this.workspaceId = payload.workspace_id || this.workspaceId;
      const modulePage = payload.module_page || {};
      const filters = modulePage.filters || {};
      this.moduleQuery = {
        page: Number(modulePage.page) > 0 ? Number(modulePage.page) : this.moduleQuery.page || 1,
        page_size: Number(modulePage.page_size) > 0 ? Number(modulePage.page_size) : this.moduleQuery.page_size || 50,
        big_module: String(filters.big_module || ""),
        function_module: String(filters.function_module || ""),
        primary_owner: String(filters.primary_owner || ""),
      };
      this.error = "";
    },
    async loadWorkspace(workspaceId = this.workspaceId) {
      this.loading = true;
      try {
        this.applyWorkspace(await apiClient.getWorkspace(workspaceId));
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
        this.applyWorkspace(await apiClient.saveDraft(this.workspaceId, payload));
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
        const mergedQuery = {
          ...this.moduleQuery,
          ...query,
        };
        const normalizedQuery = {
          page: Number(mergedQuery.page) > 0 ? Number(mergedQuery.page) : 1,
          page_size: Number(mergedQuery.page_size) > 0 ? Number(mergedQuery.page_size) : 50,
          big_module: String(mergedQuery.big_module || ""),
          function_module: String(mergedQuery.function_module || ""),
          primary_owner: String(mergedQuery.primary_owner || ""),
        };
        this.moduleQuery = normalizedQuery;
        this.applyWorkspace(await apiClient.getModules(this.workspaceId, normalizedQuery));
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
        this.applyWorkspace(await apiClient.getMembers(this.workspaceId));
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
        this.applyWorkspace(await apiClient.createMember(this.workspaceId, payload));
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
        this.applyWorkspace(await apiClient.updateMember(this.workspaceId, memberName, payload));
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
        this.applyWorkspace(await apiClient.deleteMember(this.workspaceId, memberName));
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
        this.applyWorkspace(await apiClient.generateRecommendations(this.workspaceId));
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
        this.applyWorkspace(await apiClient.deleteRecommendation(this.workspaceId, requirementId));
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
        this.applyWorkspace(await apiClient.batchDeleteRecommendations(this.workspaceId, requirementIds));
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
        this.applyWorkspace(await apiClient.confirmAssignments(this.workspaceId, actions));
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
        this.applyWorkspace(await apiClient.uploadModuleKnowledge(this.workspaceId, file));
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
        this.applyWorkspace(await apiClient.syncPlatformExports(this.workspaceId, storyFile, taskFile));
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
        this.applyWorkspace(await apiClient.uploadStoryOnly(this.workspaceId, storyFile));
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
        this.applyWorkspace(await apiClient.uploadTaskOnly(this.workspaceId, taskFile));
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
        this.taskList = payload.tasks || [];
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
        this.monitoring = payload.alerts || [];
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
        this.insights = payload.insights || this.insights;
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
        this.insightHistory = payload.history || [];
      } catch (error) {
        this.error = error.message;
        throw error;
      }
    },
    async sendChatMessage(message) {
      this.loading = true;
      try {
        const result = await apiClient.sendChatMessage(this.workspaceId, message);
        this.applyWorkspace(result);
        this.error = "";
        return result;
      } catch (error) {
        this.error = error.message;
        throw error;
      } finally {
        this.loading = false;
      }
    },
  },
});
