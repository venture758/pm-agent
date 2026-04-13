import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

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

  it("batch deletes selected recommendations", async () => {
    const store = useWorkspaceStore();
    store.workspace.recommendations = [
      buildRecommendation("R-1", "发票修复"),
      buildRecommendation("R-2", "税率调整"),
    ];
    store.batchDeleteRecommendations = vi.fn(async (ids) => {
      const removing = new Set(ids);
      store.workspace.recommendations = store.workspace.recommendations.filter(
        (item) => !removing.has(item.requirement_id),
      );
    });
    store.confirmAssignments = vi.fn(async () => {});

    const wrapper = mount(RecommendationsView);
    await wrapper.findAll('[data-test="select-row"]')[0].setValue(true);
    await wrapper.get('[data-test="batch-delete"]').trigger("click");
    expect(store.batchDeleteRecommendations).toHaveBeenCalledWith(["R-1"]);
    expect(store.workspace.recommendations).toHaveLength(1);
  });

  it("applies batch action to selected rows", async () => {
    const store = useWorkspaceStore();
    store.workspace.recommendations = [
      buildRecommendation("R-1", "发票修复"),
      buildRecommendation("R-2", "税率调整"),
    ];
    store.confirmAssignments = vi.fn(async () => {});

    const wrapper = mount(RecommendationsView);
    await wrapper.findAll('[data-test="select-row"]')[0].setValue(true);
    await wrapper.get('[data-test="batch-action"]').setValue("reassign");
    await wrapper.get('[data-test="batch-dev-owner"]').setValue("张三");
    await wrapper.get('[data-test="batch-apply"]').trigger("click");
    await wrapper.get('[data-test="submit-confirm"]').trigger("click");

    const payload = store.confirmAssignments.mock.calls[0][0];
    expect(payload["R-1"].action).toBe("reassign");
    expect(payload["R-1"].development_owner).toBe("张三");
    expect(payload["R-2"].action).toBe("accept");
  });
});
