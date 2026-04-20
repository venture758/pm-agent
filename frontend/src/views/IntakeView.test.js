import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

const mockRouterPush = vi.fn(async () => {});

vi.mock("vue-router", () => ({
  RouterLink: {
    template: "<a><slot /></a>",
  },
  useRoute: () => ({
    params: { workspaceId: "default" },
  }),
  useRouter: () => ({
    push: mockRouterPush,
  }),
}));

import IntakeView from "./IntakeView.vue";
import { useWorkspaceStore } from "../stores/workspace";

describe("IntakeView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    mockRouterPush.mockReset();
  });

  it("renders recommendation action in assistant panel and triggers generation", async () => {
    const store = useWorkspaceStore();
    store.workspace.draft = {
      draft_mode: "chat",
      message_text: "initial",
      chat_messages: [
        {
          role: "assistant",
          content: "已解析需求",
          parsed_requirements: [
            {
              requirement_id: "R-1",
              title: "示例需求",
              priority: "中",
            },
          ],
        },
      ],
      team_rows: [],
      requirement_rows: [],
    };
    store.workspace.requirements = [{ requirement_id: "R-1", title: "示例需求" }];
    store.generateRecommendations = vi.fn(async () => {});

    const wrapper = mount(IntakeView);
    expect(wrapper.text()).not.toContain("保存草稿");
    await wrapper.get("button.generate-inline-button").trigger("click");

    expect(store.generateRecommendations).toHaveBeenCalledTimes(1);
    expect(mockRouterPush).toHaveBeenCalledWith({
      name: "recommendations",
      params: { workspaceId: "default" },
    });
  });

  it("shows needs-confirmation module hints for parsed requirements", () => {
    const store = useWorkspaceStore();
    store.workspace.draft = {
      draft_mode: "chat",
      message_text: "",
      chat_messages: [
        {
          role: "assistant",
          content: "已解析需求",
          parsed_requirements: [
            {
              requirement_id: "R-2",
              title: "发票异常回滚逻辑补齐",
              priority: "中",
              big_module: "税务",
              function_module: "发票接口",
              abstract_summary: "补齐发票异常回滚场景的幂等处理",
              match_status: "needs_confirmation",
              match_evidence: ["命中关键词: 回滚"],
              candidate_modules: [
                {
                  big_module: "税务",
                  function_module: "发票接口",
                  reason: "历史任务名称关联",
                },
              ],
            },
          ],
        },
      ],
      team_rows: [],
      requirement_rows: [],
    };
    store.workspace.requirements = [{ requirement_id: "R-2", title: "发票异常回滚逻辑补齐" }];

    const wrapper = mount(IntakeView);
    const text = wrapper.text();
    expect(text).toContain("待确认模块归属");
    expect(text).toContain("候选模块");
    expect(text).toContain("补齐发票异常回滚场景的幂等处理");
  });
});
