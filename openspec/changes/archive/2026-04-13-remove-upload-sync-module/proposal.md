## Why

当前交付页保留了“上传与同步”独立模块，入口与“故事管理”中的独立故事导入能力重叠，用户需要在多个区域切换，操作路径冗长且容易误用。现在需要移除该模块，统一交付页聚焦在故事与任务管理两个核心视图。

## What Changes

- 删除交付页中的“上传与同步”Tab及其整块展示内容。
- 将交付页默认入口调整为“故事管理”，保留“任务管理”Tab。
- 清理前端仅被“上传与同步”模块使用的状态、事件与文案。
- 保留现有后端接口兼容性，不在本次变更中下线同步 API。
- 补充页面与状态管理测试，覆盖 Tab 数量、默认选中项与页面关键文案。

## Capabilities

### New Capabilities
- `delivery-page-without-upload-sync`: 交付页 SHALL 不再展示“上传与同步”模块，仅保留“故事管理”和“任务管理”工作流。

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `frontend/src/views/DeliveryView.vue`（Tab 结构、默认状态、模板区块）
  - `frontend/src/stores/workspace.js`（若存在仅供 upload-sync UI 使用的状态，清理或降级）
  - `frontend/src/views/*.test.js` / `frontend/src/stores/*.test.js`（补充或调整断言）
- APIs: 无新增 API；本次不移除已有同步接口。
- Data model: 无数据库变更。
- Risks: 用户如果仍依赖旧模块入口，需要通过故事管理页中的能力完成导入流程，需确保界面引导清晰。
