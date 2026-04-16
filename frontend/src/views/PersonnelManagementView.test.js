import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import { nextTick } from "vue";

vi.mock("vue-router", () => ({
  useRoute: () => ({
    params: { workspaceId: "default" },
  }),
}));

import PersonnelManagementView from "./PersonnelManagementView.vue";
import { useWorkspaceStore } from "../stores/workspace";

describe("PersonnelManagementView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a managed member", async () => {
    const store = useWorkspaceStore();
    store.workspace.managed_members = [
      { name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] },
    ];
    store.refreshMembers = vi.fn(async () => {});
    store.createMember = vi.fn(async () => {});
    store.updateMember = vi.fn(async () => {});
    store.deleteMember = vi.fn(async () => {});
    store.updateModule = vi.fn(async () => {});

    const wrapper = mount(PersonnelManagementView, { attachTo: document.body });

    // Open add form
    await wrapper.get(".add-trigger").trigger("click");
    await nextTick();

    // Fill name and submit
    const nameInput = wrapper.find("input[placeholder='例如：李祥']");
    await nameInput.setValue("王海林");
    await wrapper.get("button[type='submit']").trigger("click");

    expect(store.createMember).toHaveBeenCalled();
    wrapper.unmount();
  });

  it("edits and deletes a managed member", async () => {
    const store = useWorkspaceStore();
    store.workspace.managed_members = [
      { name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] },
    ];
    store.refreshMembers = vi.fn(async () => {});
    store.createMember = vi.fn(async () => {});
    store.updateMember = vi.fn(async () => {});
    store.deleteMember = vi.fn(async () => {});
    store.updateModule = vi.fn(async () => {});

    const wrapper = mount(PersonnelManagementView, { attachTo: document.body });

    // Click edit on first member card
    await wrapper.get(".action-edit").trigger("click");
    await nextTick();
    await wrapper.get(".action-save").trigger("click");
    expect(store.updateMember).toHaveBeenCalled();

    // Click delete
    vi.spyOn(window, "confirm").mockReturnValue(true);
    await wrapper.get(".action-delete").trigger("click");
    expect(store.deleteMember).toHaveBeenCalled();
    wrapper.unmount();
  });

  function mockStoreForMemberModuleBoard() {
    const store = useWorkspaceStore();
    store.workspace.managed_members = [
      { name: "李祥", role: "developer", skills: ["发票"], experience_level: "高", workload: 0.2, capacity: 1, constraints: [] },
    ];
    store.workspace.module_entries = [
      {
        key: "税务::发票接口",
        big_module: "税务",
        function_module: "发票接口",
        primary_owner: "李祥",
        backup_owners: ["王海林"],
        familiar_members: ["李祥"],
        aware_members: [],
        unfamiliar_members: [],
      },
      {
        key: "税务::发票对账",
        big_module: "税务",
        function_module: "发票对账",
        primary_owner: "王海林",
        backup_owners: ["余萍"],
        familiar_members: ["张三"],
        aware_members: ["李祥"],
        unfamiliar_members: ["王五"],
      },
      {
        key: "税务::补偿逻辑",
        big_module: "税务",
        function_module: "补偿逻辑",
        primary_owner: "余萍",
        backup_owners: [],
        familiar_members: [],
        aware_members: [],
        unfamiliar_members: ["李祥"],
      },
      {
        key: "税务::税率配置",
        big_module: "税务",
        function_module: "税率配置",
        primary_owner: "余萍",
        backup_owners: ["王海林"],
        familiar_members: [],
        aware_members: [],
        unfamiliar_members: [],
      },
    ];
    store.refreshMembers = vi.fn(async () => {});
    store.createMember = vi.fn(async () => {});
    store.updateMember = vi.fn(async () => {});
    store.deleteMember = vi.fn(async () => {});
    store.updateModule = vi.fn(async () => {});
    return store;
  }

  it("opens member module modal and shows four drag columns with all modules", async () => {
    mockStoreForMemberModuleBoard();
    const wrapper = mount(PersonnelManagementView, {
      attachTo: document.body,
      global: { stubs: { Teleport: true } },
    });

    // Click "模块" button on first card
    await wrapper.get(".action-modules").trigger("click");
    await nextTick();
    await flushPromises();

    expect(wrapper.text()).toContain("的模块熟悉度");
    expect(wrapper.findAll(".kanban-lane")).toHaveLength(4);
    expect(wrapper.find('[data-lane-key="unmarked"]').text()).toContain("税率配置");
    expect(wrapper.find('[data-lane-key="unfamiliar"]').text()).toContain("补偿逻辑");
    expect(wrapper.find('[data-lane-key="aware"]').text()).toContain("发票对账");
    expect(wrapper.find('[data-lane-key="familiar"]').text()).toContain("发票接口");
    wrapper.unmount();
  });

  it("saves member familiarity change when dragging to a new level", async () => {
    const store = mockStoreForMemberModuleBoard();

    const wrapper = mount(PersonnelManagementView, {
      attachTo: document.body,
      global: { stubs: { Teleport: true } },
    });
    await wrapper.get(".action-modules").trigger("click");
    await nextTick();
    await wrapper.find('[data-module-key="税务::发票对账"]').trigger("dragstart");
    await wrapper.find('[data-lane-key="familiar"]').trigger("drop");
    await flushPromises();

    expect(store.updateModule).toHaveBeenCalledTimes(1);
    const [moduleKey, payload] = store.updateModule.mock.calls[0];
    expect(moduleKey).toBe("税务::发票对账");
    expect(payload.original_key).toBe("税务::发票对账");
    expect(payload.familiar_members).toContain("李祥");
    expect(payload.familiar_members).toContain("张三");
    expect(payload.aware_members).not.toContain("李祥");
    expect(payload.unfamiliar_members).toContain("王五");
    expect(store.refreshMembers).toHaveBeenCalled();
    expect(window.alert).toHaveBeenCalledWith("处理成功：已更新成员模块熟悉度");
    wrapper.unmount();
  });

  it("removes member familiarity when dragging to unmarked", async () => {
    const store = mockStoreForMemberModuleBoard();

    const wrapper = mount(PersonnelManagementView, {
      attachTo: document.body,
      global: { stubs: { Teleport: true } },
    });
    await wrapper.get(".action-modules").trigger("click");
    await nextTick();
    await wrapper.find('[data-module-key="税务::补偿逻辑"]').trigger("dragstart");
    await wrapper.find('[data-lane-key="unmarked"]').trigger("drop");
    await flushPromises();

    const [, payload] = store.updateModule.mock.calls[0];
    expect(payload.familiar_members).not.toContain("李祥");
    expect(payload.aware_members).not.toContain("李祥");
    expect(payload.unfamiliar_members).not.toContain("李祥");
    wrapper.unmount();
  });

  it("rolls back drag state and shows error when saving fails", async () => {
    const store = mockStoreForMemberModuleBoard();
    store.updateModule = vi.fn(async () => {
      throw new Error("保存失败");
    });

    const wrapper = mount(PersonnelManagementView, {
      attachTo: document.body,
      global: { stubs: { Teleport: true } },
    });
    await wrapper.get(".action-modules").trigger("click");
    await nextTick();
    const refreshMembersCallCount = store.refreshMembers.mock.calls.length;

    expect(wrapper.find('[data-lane-key="aware"]').text()).toContain("发票对账");
    await wrapper.find('[data-module-key="税务::发票对账"]').trigger("dragstart");
    await wrapper.find('[data-lane-key="familiar"]').trigger("drop");
    await flushPromises();

    expect(wrapper.find('[data-lane-key="aware"]').text()).toContain("发票对账");
    expect(window.alert).toHaveBeenCalledWith("处理失败：保存失败");
    expect(store.refreshMembers.mock.calls.length).toBe(refreshMembersCallCount);
    wrapper.unmount();
  });
});
