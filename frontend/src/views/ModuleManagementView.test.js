import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";

vi.mock("vue-router", () => ({
  useRoute: () => ({
    params: { workspaceId: "default" },
  }),
}));

import ModuleManagementView from "./ModuleManagementView.vue";
import { useWorkspaceStore } from "../stores/workspace";

describe("ModuleManagementView", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("creates a managed module", async () => {
    const store = useWorkspaceStore();
    store.workspace.module_entries = [
      {
        key: "税务::发票接口",
        big_module: "税务",
        function_module: "发票接口",
        primary_owner: "李祥",
        backup_owners: ["余萍"],
        familiar_members: ["李祥"],
        aware_members: ["余萍"],
        unfamiliar_members: [],
      },
    ];
    store.refreshModules = vi.fn(async () => {});
    store.createModule = vi.fn(async () => {});
    store.updateModule = vi.fn(async () => {});
    store.deleteModule = vi.fn(async () => {});

    const wrapper = mount(ModuleManagementView);
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "新增业务模块")
      .trigger("click");
    const modal = wrapper.get(".modal-panel");
    const modalInputs = modal.findAll("input");
    await modalInputs[0].setValue("税务");
    await modalInputs[1].setValue("发票接口");
    await modalInputs[2].setValue("李祥");
    await modalInputs[3].setValue("余萍, 王海林");
    const modalTextareas = modal.findAll("textarea");
    await modalTextareas[0].setValue("李祥");
    await modalTextareas[1].setValue("余萍");
    await modalTextareas[2].setValue("王海林");
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "保存新增")
      .trigger("click");
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "保存")
      .trigger("click");
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "删除")
      .trigger("click");

    expect(store.createModule).toHaveBeenCalledWith({
      big_module: "税务",
      function_module: "发票接口",
      primary_owner: "李祥",
      backup_owners: ["余萍", "王海林"],
      familiar_members: ["李祥"],
      aware_members: ["余萍"],
      unfamiliar_members: ["王海林"],
    });
    expect(store.updateModule).toHaveBeenCalled();
    expect(store.updateModule).toHaveBeenCalledWith(
      "税务::发票接口",
      expect.objectContaining({
        original_key: "税务::发票接口",
      }),
    );
    expect(store.deleteModule).toHaveBeenCalled();
    expect(store.refreshModules).toHaveBeenCalledWith({ page: 1, page_size: 50 });
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining("处理成功"));
  });

  it("shows failure popup when save fails", async () => {
    const store = useWorkspaceStore();
    store.workspace.module_entries = [
      {
        key: "税务::发票接口",
        big_module: "税务",
        function_module: "发票接口",
        primary_owner: "李祥",
        backup_owners: ["余萍"],
        familiar_members: ["李祥"],
        aware_members: ["余萍"],
        unfamiliar_members: [],
      },
    ];
    store.refreshModules = vi.fn(async () => {});
    store.createModule = vi.fn(async () => {});
    store.updateModule = vi.fn(async () => {
      throw new Error("未找到要更新的模块条目");
    });
    store.deleteModule = vi.fn(async () => {});

    const wrapper = mount(ModuleManagementView);
    await wrapper
      .findAll("button")
      .find((button) => button.text() === "保存")
      .trigger("click");

    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining("处理失败"));
    expect(window.alert).toHaveBeenCalledWith(expect.stringContaining("未找到要更新的模块条目"));
  });
});
