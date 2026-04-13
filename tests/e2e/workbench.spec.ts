import { test, expect } from "@playwright/test";

test("workbench intake and recommendation flow", async ({ page }) => {
  await page.goto("http://127.0.0.1:5173/workspaces/default/personnel");
  await page.getByLabel("姓名").fill("李祥");
  await page.getByLabel("技能").fill("发票, 接口");
  await page.getByRole("button", { name: "新增成员" }).click();

  await page.goto("http://127.0.0.1:5173/workspaces/default/intake");
  await page.getByPlaceholder("粘贴产品经理在群里的需求列表").fill(
    "1. 发票查验接口替换 https://example.com/1 优先级高",
  );
  await page.getByRole("button", { name: "保存草稿" }).click();
  await page.getByRole("button", { name: "生成推荐" }).click();
  await page.goto("http://127.0.0.1:5173/workspaces/default/recommendations");
  await expect(page.getByText("分配建议")).toBeVisible();
});
