import { beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

vi.mock("../api/client", () => ({
  apiClient: {
    getWorkspace: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: [],
    })),
    saveDraft: vi.fn(async (_, payload) => ({
      workspace_id: "default",
      title: "default",
      draft: { ...payload, requirement_rows: payload.requirement_rows || [], team_rows: [] },
      managed_members: [],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["草稿已保存"],
    })),
    generateRecommendations: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [{ name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] }],
      module_entries: [{ key: "税务::发票接口", big_module: "税务", function_module: "发票接口", primary_owner: "李祥", backup_owner: "", familiarity_by_member: { "李祥": "熟悉" } }],
      recommendations: [{ requirement_id: "1", title: "示例需求" }],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["已生成推荐"],
    })),
    confirmAssignments: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [{ requirement_id: "1", title: "示例需求" }],
      handoff: { stories: [{ user_story_code: "NEW-STORY-1" }], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["已确认"],
    })),
    uploadModuleKnowledge: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [{ key: "税务::发票接口", big_module: "税务", function_module: "发票接口", primary_owner: "李祥", backup_owner: "", familiarity_by_member: { "李祥": "熟悉" } }],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 3, sample_keys: ["税务::发票接口"] },
      uploads: [],
      messages: ["模块知识库导入完成"],
    })),
    syncPlatformExports: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      latest_sync_batch: { batch_id: "batch-1", actions: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["平台同步完成"],
    })),
    uploadStoryOnly: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [{ user_story_code: "PRJ-00730001", name: "品牌官网优化" }], tasks: [] },
      latest_story_import: { total: 1, created: 1, updated: 0, failed: 0, errors: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["故事导入完成"],
    })),
    getModules: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [{ key: "税务::发票接口", big_module: "税务", function_module: "发票接口", primary_owner: "李祥", backup_owner: "", familiarity_by_member: { "李祥": "熟悉" } }],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 1, sample_keys: ["税务::发票接口"] },
      uploads: [],
      messages: [],
    })),
    createModule: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [{ key: "税务::发票接口", big_module: "税务", function_module: "发票接口", primary_owner: "李祥", backup_owner: "", familiarity_by_member: { "李祥": "熟悉" } }],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 1, sample_keys: ["税务::发票接口"] },
      uploads: [],
      messages: ["已新增模块 税务::发票接口"],
    })),
    updateModule: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [{ key: "税务::发票接口", big_module: "税务", function_module: "发票接口", primary_owner: "李祥", backup_owner: "", familiarity_by_member: { "李祥": "熟悉" } }],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 1, sample_keys: ["税务::发票接口"] },
      uploads: [],
      messages: ["已更新模块 税务::发票接口"],
    })),
    deleteModule: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["已删除模块 税务::发票接口"],
    })),
    getMembers: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [{ name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] }],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: [],
    })),
    createMember: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [{ name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] }],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["已新增成员 李祥"],
    })),
    updateMember: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [{ name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] }],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["已更新成员 李祥"],
    })),
    deleteMember: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: { message_text: "draft", requirement_rows: [], team_rows: [] },
      managed_members: [],
      module_entries: [],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 0, sample_keys: [] },
      uploads: [],
      messages: ["已删除成员 李祥"],
    })),
    getMonitoring: vi.fn(async () => ({ alerts: [{ reason: "risk" }] })),
    getInsights: vi.fn(async () => ({ insights: { heatmap: [{ member: "李祥" }], single_points: [], growth_suggestions: [] } })),
    sendChatMessage: vi.fn(async () => ({
      workspace_id: "default",
      title: "default",
      draft: {
        draft_mode: "chat",
        message_text: "",
        requirement_rows: [],
        team_rows: [],
        chat_messages: [
          { role: "user", content: "新增发票接口" },
          { role: "assistant", content: "已解析", parsed_requirements: [{ requirement_id: "LLM-1", title: "新增发票接口" }] },
        ],
      },
      requirements: [{ requirement_id: "LLM-1", title: "新增发票接口" }],
      managed_members: [{ name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] }],
      module_entries: [{ key: "税务::发票接口", big_module: "税务", function_module: "发票接口", primary_owner: "李祥", backup_owner: "", familiarity_by_member: { "李祥": "熟悉" } }],
      recommendations: [],
      confirmed_assignments: [],
      handoff: { stories: [], tasks: [] },
      knowledge_base_summary: { entry_count: 1, sample_keys: ["税务::发票接口"] },
      uploads: [],
      messages: ["已解析 1 条需求"],
    })),
  },
}));

import { useWorkspaceStore } from "./workspace";

describe("workspace store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("loads workspace and updates draft", async () => {
    const store = useWorkspaceStore();
    await store.loadWorkspace("default");
    expect(store.workspace.workspace_id).toBe("default");

    await store.saveDraft({ message_text: "new draft", requirement_rows: [] });
    expect(store.workspace.draft.message_text).toBe("new draft");
    expect(store.workspace.messages).toContain("草稿已保存");
  });

  it("handles recommendation, maintenance, confirmation, upload and monitoring actions", async () => {
    const store = useWorkspaceStore();
    await store.createMember({ name: "李祥", role: "developer", skills: "发票", experience: "高", workload: 0.2, capacity: 1 });
    expect(store.workspace.managed_members).toHaveLength(1);

    await store.createModule({
      big_module: "税务",
      function_module: "发票接口",
      primary_owner: "李祥",
      backup_owners: [],
      familiar_members: ["李祥"],
      aware_members: [],
      unfamiliar_members: [],
    });
    expect(store.workspace.module_entries).toHaveLength(1);

    await store.sendChatMessage("新增发票接口");
    expect(store.workspace.requirements).toHaveLength(1);
    expect(store.workspace.draft.chat_messages).toHaveLength(2);

    await store.generateRecommendations();
    expect(store.workspace.recommendations).toHaveLength(1);

    await store.confirmAssignments({ 1: { action: "accept" } });
    expect(store.workspace.confirmed_assignments).toHaveLength(1);

    await store.uploadModuleKnowledge(new File(["content"], "module.xlsx"));
    expect(store.workspace.knowledge_base_summary.entry_count).toBe(3);

    await store.syncPlatformExports(new File(["a"], "story.xlsx"), new File(["b"], "task.xlsx"));
    expect(store.workspace.latest_sync_batch.batch_id).toBe("batch-1");

    await store.uploadStoryOnly(new File(["a"], "story-only.xlsx"));
    expect(store.workspace.latest_story_import.created).toBe(1);
    expect(store.workspace.handoff.stories[0].user_story_code).toBe("PRJ-00730001");

    await store.refreshMonitoring();
    expect(store.monitoring).toHaveLength(1);

    await store.refreshInsights();
    expect(store.insights.heatmap[0].member).toBe("李祥");
  });
});
