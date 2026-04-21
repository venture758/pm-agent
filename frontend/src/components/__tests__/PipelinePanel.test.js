import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import PipelinePanel from "../PipelinePanel.vue";

// Mock workspace store
vi.mock("../../stores/workspace", () => ({
  useWorkspaceStore: () => ({
    loading: false,
    confirmPipelineStep: vi.fn(async (action) => ({
      status: action === "execute" ? "complete" : "running",
      run_status: action === "execute" ? "completed" : "running",
      execution_mode: "manual",
      step_progress: [],
    })),
  }),
}));

// Mock element-plus
vi.mock("element-plus", async (originalImport) => {
  const actual = await originalImport();
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      error: vi.fn(),
    },
    ElMessageBox: {
      prompt: vi.fn(async () => ({ value: "test feedback" })),
    },
    ElDialog: {
      name: "ElDialog",
      template: '<div class="el-dialog"><slot /><slot name="footer" /></div>',
      props: ["modelValue", "title", "width", "closeOnClickModal"],
    },
  };
});

const mockPipelineState = {
  workspace_id: "default",
  execution_mode: "manual",
  run_status: "awaiting_confirmation",
  awaiting_confirmation: false,
  blocking_reason: "",
  current_step: "requirement_parsing",
  current_step_index: 0,
  is_complete: false,
  step_progress: [
    { step: "requirement_parsing", label: "需求解析", status: "current" },
    { step: "personnel_matching", label: "人员匹配", status: "pending" },
    { step: "module_extraction", label: "模块提炼", status: "pending" },
    { step: "team_analysis", label: "梯队分析", status: "pending" },
    { step: "knowledge_update", label: "知识更新", status: "pending" },
  ],
  step_results: {},
  requirements: [
    { requirement_id: "LLM-1", title: "新增发票接口", priority: "高", complexity: "中", risk: "低", skills: ["Vue", "API"] },
  ],
  assignment_suggestions: [],
  module_changes: [],
  team_analysis: {},
  pending_changes: [],
  step_constraints: {},
  llm_stats: [],
};

function createWrapper(overrides = {}) {
  return mount(PipelinePanel, {
    props: {
      pipelineState: { ...mockPipelineState, ...overrides },
    },
    global: {
      stubs: {
        ElDialog: {
          template: '<div class="el-dialog"><slot /><slot name="footer" /></div>',
          props: ["modelValue"],
        },
      },
    },
  });
}

describe("PipelinePanel", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("renders 5 progress steps", () => {
    const wrapper = createWrapper();
    const steps = wrapper.findAll(".pipeline-step");
    expect(steps).toHaveLength(5);
    expect(steps[0].classes()).toContain("step-current");
    expect(steps[1].classes()).toContain("step-pending");
  });

  it("shows checkmark for completed steps", () => {
    const wrapper = createWrapper({
      step_progress: [
        { step: "requirement_parsing", label: "需求解析", status: "completed" },
        { step: "personnel_matching", label: "人员匹配", status: "current" },
        { step: "module_extraction", label: "模块提炼", status: "pending" },
        { step: "team_analysis", label: "梯队分析", status: "pending" },
        { step: "knowledge_update", label: "知识更新", status: "pending" },
      ],
      step_results: { requirement_parsing: { status: "confirmed" } },
      current_step: "personnel_matching",
      current_step_index: 1,
    });
    const steps = wrapper.findAll(".pipeline-step");
    expect(steps[0].classes()).toContain("step-completed");
    expect(steps[1].classes()).toContain("step-current");
  });

  it("renders requirement parsing results as table", () => {
    const wrapper = createWrapper();
    const table = wrapper.find(".requirements-table");
    expect(table.exists()).toBe(true);
    expect(wrapper.text()).toContain("新增发票接口");
    expect(wrapper.text()).toContain("高");
    expect(wrapper.text()).toContain("Vue");
  });

  it("renders personnel matching results as cards", () => {
    const wrapper = createWrapper({
      current_step: "personnel_matching",
      current_step_index: 1,
      step_progress: [
        { step: "requirement_parsing", label: "需求解析", status: "completed" },
        { step: "personnel_matching", label: "人员匹配", status: "current" },
        { step: "module_extraction", label: "模块提炼", status: "pending" },
        { step: "team_analysis", label: "梯队分析", status: "pending" },
        { step: "knowledge_update", label: "知识更新", status: "pending" },
      ],
      step_results: { requirement_parsing: { status: "confirmed" } },
      assignment_suggestions: [
        {
          requirement_id: "LLM-1",
          title: "新增发票接口",
          developer: "李祥",
          tester: "王明",
          backup: "赵强",
          collaborators: ["张伟"],
          reason: "技能匹配",
          confidence: 0.85,
        },
      ],
    });
    expect(wrapper.find(".assignment-card").exists()).toBe(true);
    expect(wrapper.text()).toContain("李祥");
    expect(wrapper.text()).toContain("0.85");
  });

  it("renders module extraction results as list", () => {
    const wrapper = createWrapper({
      current_step: "module_extraction",
      current_step_index: 2,
      step_progress: [
        { step: "requirement_parsing", label: "需求解析", status: "completed" },
        { step: "personnel_matching", label: "人员匹配", status: "completed" },
        { step: "module_extraction", label: "模块提炼", status: "current" },
        { step: "team_analysis", label: "梯队分析", status: "pending" },
        { step: "knowledge_update", label: "知识更新", status: "pending" },
      ],
      step_results: { requirement_parsing: { status: "confirmed" }, personnel_matching: { status: "confirmed" } },
      module_changes: [
        { change_type: "create_big_module", module_name: "支付中心", reason: "新业务领域" },
      ],
    });
    expect(wrapper.find(".module-changes").exists()).toBe(true);
    expect(wrapper.text()).toContain("支付中心");
  });

  it("renders team analysis results", () => {
    const wrapper = createWrapper({
      current_step: "team_analysis",
      current_step_index: 3,
      step_progress: [
        { step: "requirement_parsing", label: "需求解析", status: "completed" },
        { step: "personnel_matching", label: "人员匹配", status: "completed" },
        { step: "module_extraction", label: "模块提炼", status: "completed" },
        { step: "team_analysis", label: "梯队分析", status: "current" },
        { step: "knowledge_update", label: "知识更新", status: "pending" },
      ],
      step_results: { requirement_parsing: { status: "confirmed" }, personnel_matching: { status: "confirmed" }, module_extraction: { status: "confirmed" } },
      team_analysis: {
        single_points: [
          { module: "支付中心", member: "李祥", severity: "high", suggestion: "培养B角" },
        ],
        growth_suggestions: [
          { member: "王明", suggestion: "学习支付系统" },
        ],
      },
    });
    expect(wrapper.find(".risk-table").exists()).toBe(true);
    expect(wrapper.text()).toContain("支付中心");
    expect(wrapper.text()).toContain("培养B角");
  });

  it("renders knowledge update summary stats", () => {
    const wrapper = createWrapper({
      current_step: "knowledge_update",
      current_step_index: 4,
      step_progress: [
        { step: "requirement_parsing", label: "需求解析", status: "completed" },
        { step: "personnel_matching", label: "人员匹配", status: "completed" },
        { step: "module_extraction", label: "模块提炼", status: "completed" },
        { step: "team_analysis", label: "梯队分析", status: "completed" },
        { step: "knowledge_update", label: "知识更新", status: "current" },
      ],
      step_results: { requirement_parsing: { status: "confirmed" }, personnel_matching: { status: "confirmed" }, module_extraction: { status: "confirmed" }, team_analysis: { status: "confirmed" } },
      requirements: [{}, {}],
      assignment_suggestions: [{}, {}],
      module_changes: [{}],
      pending_changes: [{ description: "更新模块知识库" }],
    });
    expect(wrapper.find(".summary-stats").exists()).toBe(true);
    expect(wrapper.text()).toContain("需求解析数");
    expect(wrapper.text()).toContain("人员分配数");
  });

  it("shows 4 action buttons", () => {
    const wrapper = createWrapper();
    const buttons = wrapper.findAll(".action-btn");
    expect(buttons).toHaveLength(4);
    expect(buttons[0].text()).toBe("确认");
    expect(buttons[1].text()).toBe("修改");
    expect(buttons[2].text()).toBe("重新分析");
    expect(buttons[3].text()).toBe("跳过");
  });

  it("shows execute button on last step", () => {
    const wrapper = createWrapper({
      current_step: "knowledge_update",
      current_step_index: 4,
      step_progress: [
        { step: "requirement_parsing", label: "需求解析", status: "completed" },
        { step: "personnel_matching", label: "人员匹配", status: "completed" },
        { step: "module_extraction", label: "模块提炼", status: "completed" },
        { step: "team_analysis", label: "梯队分析", status: "completed" },
        { step: "knowledge_update", label: "知识更新", status: "current" },
      ],
      step_results: { requirement_parsing: { status: "confirmed" }, personnel_matching: { status: "confirmed" }, module_extraction: { status: "confirmed" }, team_analysis: { status: "confirmed" } },
    });
    const confirmBtn = wrapper.find(".btn-confirm");
    expect(confirmBtn.text()).toBe("执行变更");
  });

  it("shows loading bar while auto pipeline is running", () => {
    const wrapper = createWrapper({
      execution_mode: "auto",
      run_status: "running",
    });
    expect(wrapper.find(".loading-bar").exists()).toBe(true);
    expect(wrapper.findAll(".action-btn")).toHaveLength(0);
  });

  it("shows blocking reason and resume action when auto pipeline pauses", () => {
    const wrapper = createWrapper({
      execution_mode: "auto",
      run_status: "awaiting_confirmation",
      awaiting_confirmation: true,
      blocking_reason: "需求解析存在待确认模块归属",
    });
    expect(wrapper.text()).toContain("需求解析存在待确认模块归属");
    expect(wrapper.find(".btn-confirm").text()).toBe("继续自动执行");
  });

  it("emits close event when close button clicked", async () => {
    const wrapper = createWrapper();
    await wrapper.find(".close-btn").trigger("click");
    expect(wrapper.emitted("close")).toHaveLength(1);
  });
});
