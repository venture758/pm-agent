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
});
