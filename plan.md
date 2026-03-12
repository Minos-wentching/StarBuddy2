# 改进计划 v2：UI 对齐 + 性能优化 + 灵魂共振 AI Agent

---

## Phase 1：UI 统一 — Settings / History / Analytics 改为暗色 glassmorphism

三个旧页面（Settings、History、Analytics）目前使用 Vuetify 默认亮色主题（`v-container`、白底 `v-card outlined`），与 Home/Report/Social/Immersive 的暗色 glassmorphism 风格完全脱节。

### 统一设计规范（对齐 Home.vue）

| 属性 | 值 |
|------|-----|
| 根容器 | `position: fixed; inset: 0; overflow: hidden` |
| 背景 | `<ShaderBackground role="manager" :intensity="0.15" />` |
| 滚动容器 | `max-width: 600px; margin: 0 auto; padding: 24px 20px 60px; height: 100vh; overflow-y: auto; position: relative; z-index: 10` |
| glass-card | `background: rgba(255,255,255,0.06); backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 16px` |
| 页面标题 | `font-size: 28px; font-weight: 700; color: white; letter-spacing: 2px; text-align: center` |
| 副标题 | `font-size: 14px; color: rgba(255,255,255,0.5)` |
| 返回按钮 | 左上角 `<v-btn icon variant="text" size="small">` + `color: rgba(255,255,255,0.6)` |
| 正文 | `font-size: 13-14px; color: rgba(255,255,255,0.7); line-height: 1.6` |
| 辅助文字 | `font-size: 11-12px; color: rgba(255,255,255,0.4-0.5)` |
| 表单组件 | `color="white" base-color="rgba(255,255,255,0.4)"` + `:deep` 覆写 |

### 1a. Settings.vue 改造
- 移除 `v-container`，改为 fixed 根 + ShaderBackground + 滚动容器
- `v-card outlined` → glass-card div，分节标题用 section-title 样式
- 表单 `v-text-field`/`v-select`/`v-switch` 加暗色 `:deep` 覆写
- `v-dialog` 加暗色背景（`rgba(30,30,50,0.95)`）
- 返回按钮改为左上角 icon

### 1b. History.vue 改造
- 同上根容器改造
- `v-list` → 自定义快照列表，每项用 glass-card + 人格色彩左边框
- 筛选器用暗色表单
- `v-pagination` 加暗色覆写
- 快照详情展开用 glass-card

### 1c. Analytics.vue 改造
- 同上根容器改造
- 所有 `v-card outlined` → glass-card
- `v-progress-linear` 保持 inline bg-color（已是暗色）
- `v-chip` 改为半透明样式
- `v-avatar` 改为 glass 背景

---

## Phase 2：性能优化

### 2a. RAG 模块预加载与保持（关键瓶颈）

**现状问题：**
- embedding 模型已在 `main.py` lifespan 中预加载 ✓
- 但 `MemoryStore`（ChromaDB client）是懒加载的，首次请求时才创建 PersistentClient + 获取 collection
- `VersionService` 每次请求都创建新的 `chromadb.PersistentClient`（version_service.py:37），极其浪费
- `store_report()` 在 `process_message()` 中同步阻塞执行，多次调用 `model.encode()`

**改动：**
- **main.py lifespan**：预初始化 MemoryStore 单例（`MemoryStore()` 触发 ChromaDB client 创建）
- **version_service.py**：改为单例模式或共享 MemoryStore 的 ChromaDB client，避免每次请求创建新 client
- **dialogue_service.py**：将 `store_report()` 改为 background_task（与 `store_memory` 一样），避免阻塞事件循环
- **memory_service.py**：给 `_kw_cache` 加 LRU 限制（maxsize=500），防止无限增长

### 2b. 前端 API 超时 + 请求取消
- `dialogue.js`：apiClient 加 `timeout: 30000`
- `sendMessage` 加 AbortController 防重复提交

### 2c. ShaderBackground 移动端降级
- 检测 `matchMedia('(hover: none)')` 或 `prefers-reduced-motion`
- 移动端：pixelRatio 降为 1，fbm 循环从 5→3，粒子从 20→8
- 关闭 `antialias`（全屏 shader 无需 MSAA）
- `powerPreference` 改为 `'default'`
- resize 加 debounce（150ms）
- 加 `document.visibilitychange` 暂停/恢复动画

### 2d. Vite 构建优化
- `sourcemap: false`（生产环境）
- `manualChunks`：three.js 单独分包，vue+pinia+axios 分包
- Three.js 改为按需导入（`import { WebGLRenderer, Scene, ... } from 'three'`）

### 2e. SSE 去重 + 小优化
- `useSSE.js`：`disconnect()` 时清除 `healthCheckInterval`
- `lastEventTime` 改用 `Date.now()` 数字，节流更新频率
- 确保 App.vue 和 Home.vue 不会同时创建两个 SSE 连接

### 2f. dialogue store 优化
- `lastResponse`：`filter()` → `findLast()`，O(n) → O(1)
- `getSessionSummary()`：4 次 filter → 单次循环累计

---

## Phase 3：灵魂共振 AI Agent 系统

### 3a. 预设 5 个 AI Agent 人格（后端 social_endpoints.py）

| Agent | 主题 | 核心信念 | exiles | firefighters |
|-------|------|----------|--------|-------------|
| 小星 | 完美主义 | "我必须做到最好才值得被爱" | 害怕犯错的小孩，总觉得自己不够好 | 不断鞭策自己的骑士，用忙碌逃避焦虑 |
| 小海 | 被遗弃 | "我总是被留下的那一个" | 害怕孤独的小孩，渴望被看见 | 讨好别人的骑士，不敢说不 |
| 小山 | 自我价值 | "我不够好，不配拥有好的东西" | 自卑的小孩，觉得自己是多余的 | 用成就证明自己的骑士，停不下来 |
| 小风 | 情绪压抑 | "表达情绪是软弱的表现" | 被禁止哭泣的小孩，学会了沉默 | 用理性隔离情感的骑士，什么都"没关系" |
| 小光 | 过度负责 | "别人的痛苦就是我的责任" | 被迫长大的小孩，从小照顾别人 | 拼命照顾所有人的骑士，忘了自己 |

每个 Agent 包含：
- `core_beliefs` 向量（用于余弦相似度排序）
- 人格画像文本
- 专属对话 system prompt

### 3b. 修改 `GET /api/social/similarity`
- 真实用户匹配之外，始终注入 AI Agent（也参与相似度排序）
- 返回结果加 `is_agent: true` 标记
- 保证至少返回 3 个结果

### 3c. 新增 `POST /api/social/agent-chat`
- 接收 `{ agent_id, message, history }`
- system prompt = Agent 专属 prompt + 用户人格画像
- 使用 ExternalAPIService 调用 LLM
- 对话历史存前端 localStorage（轻量方案）

### 3d. Social.vue 前端改造
- AI Agent 卡片加 ✦ 标识 + "开始对话"按钮
- 新增对话弹窗/抽屉：Agent 画像 + 聊天消息列表 + 输入框
- 消息存 `localStorage('social_chat_{agentId}')`

---

## 并行执行策略

| 并行组 | 任务 | 涉及文件 |
|--------|------|----------|
| A1 | Settings.vue 改造 | Settings.vue |
| A2 | History.vue 改造 | History.vue |
| A3 | Analytics.vue 改造 | Analytics.vue |
| B1 | RAG 预加载 + store_report 异步化 | main.py, memory_service.py, dialogue_service.py, version_service.py |
| B2 | 前端性能（ShaderBg + Vite + SSE + store） | ShaderBackground.vue, vite.config.js, useSSE.js, dialogue.js(store), dialogue.js(api) |
| C1 | AI Agent 后端 | social_endpoints.py |
| C2 | AI Agent 前端 | Social.vue |

A1/A2/A3 并行，B1/B2 并行，C1/C2 并行。三组之间无依赖，可全部同时启动。
