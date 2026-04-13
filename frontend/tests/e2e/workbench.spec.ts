import { expect, test } from "@playwright/test";

test("workbench intake and recommendation flow", async ({ page }) => {
  await page.goto("/workspaces/default/intake");
  await expect(page.locator(".metric-grid")).toHaveCount(0);
  await expect(page.locator(".mini-stat-grid")).toHaveCount(0);
  await expect(page.getByText("工作区消息")).toHaveCount(0);
  await page.getByPlaceholder("粘贴产品经理在群里的需求列表").fill(
    "1. 发票查验接口替换 https://example.com/1 优先级高",
  );
  await page.getByRole("button", { name: "保存草稿" }).click();
  await page.getByRole("button", { name: "生成推荐" }).click();
  await page.goto("/workspaces/default/recommendations");
  await expect(page.locator(".mini-stat-grid")).toHaveCount(0);
  await expect(page.getByText("工作区消息")).toHaveCount(0);
  await expect(page.getByText("分配建议")).toBeVisible();
});
