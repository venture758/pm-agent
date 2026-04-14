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
    expect(wrapper.get('[data-test="tab-history"]').classes()).toContain("tab-item--active");
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
});
