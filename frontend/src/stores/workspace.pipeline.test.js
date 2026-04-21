import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { createPinia, setActivePinia } from "pinia";

const { apiClientMock } = vi.hoisted(() => ({
  apiClientMock: {
  startPipeline: vi.fn(async (_, __, executionMode) => ({
    workspace_id: "default",
    execution_mode: executionMode,
    run_status: executionMode === "auto" ? "queued" : "awaiting_confirmation",
    status: executionMode === "auto" ? "queued" : "awaiting_confirmation",
    awaiting_confirmation: executionMode === "manual",
    current_step: "requirement_parsing",
    step_progress: {
      requirement_parsing: "in_progress",
      personnel_matching: "pending",
      module_extraction: "pending",
      team_analysis: "pending",
      knowledge_update: "pending",
    },
    step_results: {},
  })),
  getPipelineState: vi.fn(async () => ({
    workspace_id: "default",
    execution_mode: "auto",
    run_status: "running",
    status: "running",
    awaiting_confirmation: false,
    current_step: "personnel_matching",
    step_progress: {
      requirement_parsing: "completed",
      personnel_matching: "in_progress",
      module_extraction: "pending",
      team_analysis: "pending",
      knowledge_update: "pending",
    },
    step_results: {
      requirement_parsing: {
        summary: "需求解析完成",
        requirements: [{ requirement_id: "REQ-1", title: "新增发票接口" }],
      },
    },
  })),
  confirmPipelineStep: vi.fn(async () => ({
    workspace_id: "default",
    execution_mode: "auto",
    run_status: "awaiting_confirmation",
    status: "awaiting_confirmation",
    awaiting_confirmation: true,
    blocking_reason: "需求解析存在待确认模块归属",
    current_step: "personnel_matching",
    step_progress: {
      requirement_parsing: "completed",
      personnel_matching: "in_progress",
      module_extraction: "pending",
      team_analysis: "pending",
      knowledge_update: "pending",
    },
    step_results: {
      requirement_parsing: {
        summary: "需求解析完成",
        requirements: [{ requirement_id: "REQ-1", title: "新增发票接口" }],
      },
    },
  })),
  },
}));

vi.mock("../api/client", () => ({
  apiClient: apiClientMock,
}));

import { useWorkspaceStore } from "./workspace";

describe("workspace pipeline store", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts auto pipeline and polls state in background", async () => {
    const store = useWorkspaceStore();

    await store.startPipeline("", "auto");
    expect(store.pipelineState.execution_mode).toBe("auto");
    expect(store.pipelineState.run_status).toBe("queued");
    expect(store.pipelineActive).toBe(true);

    await vi.advanceTimersByTimeAsync(2100);
    expect(apiClientMock.getPipelineState).toHaveBeenCalledTimes(1);
    expect(store.pipelineState.current_step).toBe("personnel_matching");

    store.pipelineState = null;
    store.syncPipelinePolling();
  });

  it("keeps manual pipeline in confirmation mode without polling", async () => {
    const store = useWorkspaceStore();

    await store.startPipeline("", "manual");
    expect(store.pipelineState.execution_mode).toBe("manual");
    expect(store.pipelineState.run_status).toBe("awaiting_confirmation");

    await vi.advanceTimersByTimeAsync(2100);
    expect(apiClientMock.getPipelineState).not.toHaveBeenCalled();
  });

  it("updates paused auto state after confirm action", async () => {
    const store = useWorkspaceStore();

    await store.confirmPipelineStep("confirm");
    expect(store.pipelineState.awaiting_confirmation).toBe(true);
    expect(store.pipelineState.blocking_reason).toContain("待确认");
  });
});
