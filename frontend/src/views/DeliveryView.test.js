import { beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

import DeliveryView from "./DeliveryView.vue";
import { useWorkspaceStore } from "../stores/workspace";

describe("DeliveryView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
  });

  it("shows only stories/tasks tabs and defaults to stories", () => {
    const store = useWorkspaceStore();
    store.workspace.handoff.stories = [{ user_story_code: "US-1", user_story_name: "故事A", priority: "中" }];
    store.workspace.handoff.tasks = [{ task_code: "TK-1", name: "任务A", owner: "张三", task_type: "开发", planned_person_days: 1 }];

    const wrapper = mount(DeliveryView);

    const tabs = wrapper.findAll("button.tab-item");
    expect(tabs).toHaveLength(2);
    expect(tabs[0].text()).toContain("故事管理");
    expect(tabs[1].text()).toContain("任务管理");
    expect(wrapper.text()).not.toContain("上传与同步");

    const activeTab = wrapper.find("button.tab-item--active");
    expect(activeTab.exists()).toBe(true);
    expect(activeTab.text()).toContain("故事管理");
  });

  it("does not render upload-sync panel content", () => {
    const wrapper = mount(DeliveryView);

    expect(wrapper.text()).not.toContain("上传并同步平台数据");
    expect(wrapper.text()).not.toContain("同步批次明细");
    expect(wrapper.text()).not.toContain("执行同步");
  });

  it("switches between stories and tasks tabs", async () => {
    const store = useWorkspaceStore();
    store.workspace.handoff.tasks = [{ task_code: "TK-1", name: "任务A", owner: "张三", task_type: "开发", planned_person_days: 1 }];

    const wrapper = mount(DeliveryView);
    await wrapper.findAll("button.tab-item")[1].trigger("click");

    const activeTab = wrapper.find("button.tab-item--active");
    expect(activeTab.text()).toContain("任务管理");
    expect(wrapper.text()).toContain("任务管理");
  });
});
