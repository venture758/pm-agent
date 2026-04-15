## Why

当前需求输入页面是一个居中的单卡片布局，没有侧边导航。用户希望参考 ChatGPT 的交互模式：左侧可折叠的历史会话栏 + 中间主对话区域。这种模式的优势在于：

1. 会话历史始终可见，切换更直观
2. "新对话"按钮固定在侧边栏顶部，一目了然
3. 主区域专注于对话内容，视觉更干净
4. 移动端侧边栏可收起/展开，适应小屏

## What Changes

- 页面布局改为：左侧可折叠会话栏 + 右侧主对话区域
- 左侧栏顶部是 "新对话" 按钮
- 下方列出历史会话（按时间分组）
- 点击会话切换，右侧加载对应消息
- 主区域无对话时显示欢迎引导
- 移动端左侧栏默认收起，可点击汉堡菜单展开
- 移除原有的头部按钮和抽屉式交互

## Capabilities

### New Capabilities
- `chatgpt-style-intake`: ChatGPT 风格的需求输入页面 — 左侧可折叠会话栏 + 主对话区域的交互模式

### Modified Capabilities
- 无后端或 API 改动，仅前端 UI 交互变更

## Impact

- **前端**: `IntakeView.vue` 整体布局重构，从居中卡片改为左右双栏
- 无后端、API 或数据模型改动
- 后端 store actions（`createNewSession`, `switchSession`, `loadSessions`）已在 `chat-style-intake` 中实现，可直接复用
