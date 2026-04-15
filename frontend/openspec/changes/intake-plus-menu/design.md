## Context

当前 `IntakeView.vue` 使用居中卡片布局，会话切换通过顶部两个按钮（"新对话" + "历史"）和侧边抽屉完成。用户希望改为 ChatGPT 风格的左右双栏布局：左侧固定会话栏（含"新对话"按钮和历史列表），右侧主对话区域。后端 API 和 store 已在 `chat-style-intake` 中完成。

## Goals / Non-Goals

**Goals:**
- 左侧固定会话栏，包含"新对话"按钮和历史会话列表
- 右侧主对话区域，无消息时显示欢迎引导
- 侧边栏可折叠收起
- 移动端侧边栏默认隐藏，汉堡菜单展开

**Non-Goals:**
- 不改后端 API、数据模型或 store actions
- 不做会话搜索/分组/重命名/删除
- 不改 ChatView 组件的聊天消息渲染

## Decisions

### Decision 1: 左右双栏用 flexbox 实现

外层 `display: flex`，左侧栏固定宽度 260px，右侧 `flex: 1` 自适应。侧边栏收起时宽度缩到 48px（仅显示图标）或完全隐藏。

### Decision 2: 复用现有 store 逻辑

`chat-style-intake` 已实现 `createNewSession()`, `switchSession()`, `loadSessions()` 和 `session_list` / `activeSessionId` 状态。IntakeView 只需重构模板和样式，不新增 store 代码。

### Decision 3: 侧边栏会话项简化

去掉 drawer 模式中的复杂项（已确认状态标签、消息数），改用更简洁的样式：预览文字 + 相对时间，与 ChatGPT 的会话列表视觉风格对齐。

### Decision 4: 折叠交互用 CSS transition

侧边栏宽度变化通过 CSS `transition: width 0.2s ease` 实现平滑动画，配合 `overflow: hidden` 裁剪超出部分。

## Risks / Trade-offs

[侧边栏占用主区域宽度] → 默认 260px 足够展示会话预览，支持折叠到 48px 释放空间

[长会话列表滚动] → sidebar 内 `overflow-y: auto`，独立于聊天消息滚动

[移动端侧边栏遮挡] → 使用 `position: fixed` overlay 模式，背景半透明遮罩
