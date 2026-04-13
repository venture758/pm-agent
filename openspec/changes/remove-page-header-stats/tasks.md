## 1. 页面模板精简

- [x] 1.1 更新 `frontend/src/App.vue`，移除工作台主内容区头部的全局统计卡片模块并保留标题、说明和状态标签
- [x] 1.2 更新 `frontend/src/views/RecommendationsView.vue`、`frontend/src/views/MonitoringView.vue`、`frontend/src/views/InsightsView.vue`，移除各页首屏统计卡片模块并保持主操作可见
- [x] 1.3 更新 `frontend/src/views/DeliveryView.vue` 与 `frontend/src/views/IntakeView.vue`，移除首屏或上半区的统计卡片模块并保持上传区、预览区和表单区正常衔接

## 2. 状态与样式清理

- [x] 2.1 清理仅用于头部统计模块的 `computed` 汇总状态和模板绑定，避免保留未使用的派生数据
- [x] 2.2 更新 `frontend/src/assets/main.css`，删除或调整 `metric-grid`、`mini-stat-grid`、`metric-card`、`mini-stat-card` 及相关响应式样式，消除残留空白

## 3. 验证与回归检查

- [x] 3.1 更新受影响的前端测试断言，确保不再依赖已删除的统计卡片文案或结构
- [x] 3.2 运行前端测试或构建校验，确认各页面在移除统计模块后仍能正常渲染和交互

## 4. 工作区消息模块移除

- [x] 4.1 更新 `frontend/src/App.vue`，移除共享 `MessagePanel` 注入，确保各页面不再显示“工作区消息”模块
- [x] 4.2 清理 `frontend/src/components/MessagePanel.vue` 及 `frontend/src/assets/main.css` 中仅用于消息面板的残留代码
- [x] 4.3 更新相关前端断言并重新运行测试或构建校验，确认移除消息模块后页面仍正常渲染
