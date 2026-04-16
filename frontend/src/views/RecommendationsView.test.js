import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

const mockRoute = {
  params: { workspaceId: "default" },
  query: {},
};
const mockRouterReplace = vi.fn(async () => {});

vi.mock("vue-router", () => ({
  useRoute: () => mockRoute,
  useRouter: () => ({
    replace: mockRouterReplace,
  }),
}));

import RecommendationsView from "./RecommendationsView.vue";
import { useWorkspaceStore } from "../stores/workspace";

function buildRecommendation(requirementId, title) {
  return {
    requirement_id: requirementId,
    title,
    module_name: "税务发票",
    development_owner: "李祥",
    testing_owner: "余萍",
    backup_owner: "王海林",
    collaborators: [],
    split_suggestion: "",
    reasons: ["命中模块负责人"],
    unassigned_reason: "",
    workload_snapshot: { 李祥: 0.4 },
    confidence: 0.82,
  };
}

describe("RecommendationsView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockRoute.query = {};
    mockRouterReplace.mockReset();
    const store = useWorkspaceStore();
    store.loadConfirmationHistory = vi.fn(async () => {});
    store.loadKnowledgeUpdateModuleDiffs = vi.fn(async () => []);
  });

  it("deletes a recommendation immediately", async () => {
    const store = useWorkspaceStore();
    store.workspace.recommendations = [
      buildRecommendation("R-1", "发票修复"),
      buildRecommendation("R-2", "税率调整"),
    ];
    store.deleteRecommendation = vi.fn(async (requirementId) => {
      store.workspace.recommendations = store.workspace.recommendations.filter(
        (item) => item.requirement_id !== requirementId,
      );
    });
    store.confirmAssignments = vi.fn(async () => {});

    const wrapper = mount(RecommendationsView);
    await wrapper.findAll('[data-test="row-delete"]')[1].trigger("click");
    expect(store.deleteRecommendation).toHaveBeenCalledWith("R-2");
    expect(store.workspace.recommendations).toHaveLength(1);
  });

  it("submits edited confirmation payload from the secondary panel", async () => {
    const store = useWorkspaceStore();
    store.workspace.recommendations = [
      buildRecommendation("R-1", "发票修复"),
      buildRecommendation("R-2", "税率调整"),
    ];
    store.confirmAssignments = vi.fn(async () => {});

    const wrapper = mount(RecommendationsView);
    await wrapper.findAll("button.expand-btn")[0].trigger("click");
    await wrapper.find(".expand-actions select").setValue("reassign");
    await wrapper.find(".expand-actions input").setValue("张三");
    await wrapper.get('[data-test="submit-confirm"]').trigger("click");

    const payload = store.confirmAssignments.mock.calls[0][0];
    expect(payload["R-1"].action).toBe("reassign");
    expect(payload["R-1"].development_owner).toBe("张三");
    expect(payload["R-2"].action).toBe("accept");
  });

  it("opens history tab from route query", async () => {
    mockRoute.query = { tab: "history" };
    const store = useWorkspaceStore();
    store.loadConfirmationHistory = vi.fn(async () => {});

    const wrapper = mount(RecommendationsView);

    expect(wrapper.text()).toContain("确认历史");
    expect(wrapper.get('[data-test="tab-history"]').classes()).toContain("sub-nav-link--active");
    expect(store.loadConfirmationHistory).toHaveBeenCalledWith(1);
  });

  it("syncs tab changes back to route query", async () => {
    const store = useWorkspaceStore();
    store.loadConfirmationHistory = vi.fn(async () => {});

    const wrapper = mount(RecommendationsView);

    await wrapper.get('[data-test="tab-history"]').trigger("click");
    expect(mockRouterReplace).toHaveBeenCalledWith({
      name: "recommendations",
      params: { workspaceId: "default" },
      query: { tab: "history" },
    });

    mockRoute.query = { tab: "history" };
    await wrapper.get('[data-test="tab-recommendations"]').trigger("click");
    expect(mockRouterReplace).toHaveBeenLastCalledWith({
      name: "recommendations",
      params: { workspaceId: "default" },
      query: {},
    });
  });

  it("shows latest knowledge update summary on confirmation tab", async () => {
    const store = useWorkspaceStore();
    store.workspace.latest_knowledge_update = {
      session_id: "session-1",
      status: "success",
      reply: "建议培养模块备份并补充模块归类。",
      triggered_at: "2026-04-14T14:20:00",
      knowledge_updates: {
        suggested_familiarity: [{ member: "李祥" }],
        suggested_modules: [{ big_module: "税务", function_module: "发票网关" }],
      },
      optimization_suggestions: [{ type: "single_point", suggestion: "培养 B 角" }],
      has_module_diff_records: true,
      module_change_count: 1,
      requirement_change_count: 1,
      module_diff_records: [
        {
          requirement_id: "R-1",
          requirement_title: "发票修复",
          module_key: "税务::发票接口",
          changed: true,
          before_snapshot: { primary_owner: "李祥" },
          after_snapshot: { primary_owner: "李祥", recent_assignees: ["李祥"] },
          diff_summary: { changed_field_count: 1 },
        },
      ],
      error_message: "",
    };

    const wrapper = mount(RecommendationsView);

    expect(wrapper.get('[data-test="latest-knowledge-update"]').text()).toContain("最近一次知识更新");
    expect(wrapper.text()).toContain("建议培养模块备份并补充模块归类。");
    expect(wrapper.text()).toContain("熟悉度建议 1");
    expect(wrapper.text()).toContain("模块建议 1");
    expect(wrapper.text()).toContain("优化建议 1");
    expect(wrapper.text()).toContain("模块变更 1");
    expect(wrapper.get('[data-test="latest-knowledge-module-diffs"]').text()).toContain("税务::发票接口");
  });

  it("shows knowledge update status and error in history tab", async () => {
    mockRoute.query = { tab: "history" };
    const store = useWorkspaceStore();
    store.confirmationHistory.items = [
      {
        session_id: "session-2",
        confirmed_count: 1,
        created_at: "2026-04-14T14:20:00",
        confirmed_assignments: [
          {
            requirement_id: "R-1",
            title: "发票修复",
            development_owner: "李祥",
            testing_owner: "余萍",
            backup_owner: "王海林",
          },
        ],
        knowledge_update: {
          status: "failed",
          has_module_diff_records: false,
          reply: "",
          knowledge_updates: {},
          optimization_suggestions: [],
          error_message: "LLM 返回非 JSON",
        },
      },
    ];
    store.confirmationHistory.total = 1;
    store.loadConfirmationHistory = vi.fn(async () => {});

    const wrapper = mount(RecommendationsView);

    expect(wrapper.get('[data-test="history-knowledge-status"]').text()).toContain("失败");
    await wrapper.find(".h-summary-row").trigger("click");
    expect(wrapper.text()).toContain("失败原因：LLM 返回非 JSON");
  });

  it("loads and shows requirement-scoped module diff records in history", async () => {
    mockRoute.query = { tab: "history" };
    const store = useWorkspaceStore();
    store.confirmationHistory.items = [
      {
        session_id: "session-3",
        confirmed_count: 1,
        created_at: "2026-04-14T14:20:00",
        confirmed_assignments: [
          {
            requirement_id: "R-9",
            title: "税务修复",
            development_owner: "李祥",
            testing_owner: "余萍",
            backup_owner: "王海林",
          },
        ],
        knowledge_update: {
          status: "success",
          has_module_diff_records: true,
          module_change_count: 1,
          requirement_change_count: 1,
          knowledge_updates: {},
          optimization_suggestions: [],
          reply: "已更新模块知识",
          error_message: "",
        },
      },
    ];
    store.confirmationHistory.total = 1;
    store.loadConfirmationHistory = vi.fn(async () => {});
    store.loadKnowledgeUpdateModuleDiffs = vi.fn(async () => {
      store.knowledgeUpdateModuleDiffs["session-3::R-9"] = {
        loaded: true,
        loading: false,
        items: [
          {
            requirement_id: "R-9",
            requirement_title: "税务修复",
            module_key: "税务::发票接口",
            changed: true,
            before_snapshot: { primary_owner: "李祥" },
            after_snapshot: { primary_owner: "李祥", recent_assignees: ["李祥"] },
            diff_summary: { changed_field_count: 1 },
          },
        ],
      };
      return store.knowledgeUpdateModuleDiffs["session-3::R-9"].items;
    });

    const wrapper = mount(RecommendationsView);
    await wrapper.find(".h-summary-row").trigger("click");

    expect(store.loadKnowledgeUpdateModuleDiffs).toHaveBeenCalledWith("session-3", "R-9");
    expect(wrapper.get('[data-test="history-module-diffs"]').text()).toContain("税务::发票接口");
    expect(wrapper.text()).toContain("更新前");
    expect(wrapper.text()).toContain("更新后");
  });
});
