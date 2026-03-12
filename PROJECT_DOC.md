# MultiMe IFS - 灵魂共振与内在疗愈 AI Agent 系统

## 1. 产品简介 (Product Introduction)

**MultiMe IFS** 是一款基于 **IFS（内部家庭系统疗法，Internal Family Systems）** 心理学模型的 AI 驱动心理疗愈与自我探索平台。

在现代快节奏生活中，人们常常面临内心的冲突与精神内耗（例如：“理智告诉我应该努力，但情感上我只想逃避”）。MultiMe IFS 将这些内心冲突具象化为不同的“次人格（Sub-personas）”，通过多智能体（Multi-Agent）协同技术，帮助用户看见、理解并接纳自己内心的不同声音，最终实现内在的和谐与自我疗愈。

**核心价值**：
- **具象化内心冲突**：将抽象的心理压力转化为可对话、可感知的具体人格。
- **无评判的倾听**：提供一个绝对安全、温暖、无说教的倾听空间。
- **促进自我和解**：通过 AI 代理之间的“内心议会”辩论，引导用户达成内在和解。

---

## 2. 核心功能 (Core Features)

### 2.1 沉浸式对话疗愈 (Immersive Healing Dialogue)
- **Manager（管理者）主导**：系统默认以温和、包容的“管理者”身份与用户对话，提供情感支持而非生硬的建议。
- **动态情绪感知**：实时分析用户输入的情绪强度，动态调整回复的语气和深度。

### 2.2 动态人格切换 (Dynamic Persona Switching)
当用户情绪波动超过阈值时，系统会自动切换到对应的次人格状态：
- **Exiles（流放者）**：代表脆弱、受伤、被压抑的原始情感（如恐惧、孤独）。
- **Firefighters（消防员）**：代表防御机制、内化的批判声音或强烈的保护欲（如完美主义、逃避）。

### 2.3 内心议会 (Inner Council Debate)
- 当系统检测到用户内心存在强烈冲突时，会自动触发“内心议会”。
- **Exiles** 和 **Firefighters** 两个 AI Agent 会在 **Counselor（咨询师）** Agent 的引导下展开自主辩论。
- 用户可以旁观自己内心的两种声音如何对话，最终由 Counselor 总结出和解方案。

### 2.4 灵魂共振 (Soul Resonance)
- 预设了多个具有典型心理特征的 AI Agent（如：完美主义的“小星”、害怕被遗弃的“小海”等）。
- 用户可以与这些 Agent 互动，在“照镜子”的过程中产生灵魂共振，获得共鸣与启发。

### 2.5 记忆与信念追踪 (Memory & Belief Tracking)
- 自动提取用户对话中的“核心信念（Core Beliefs）”和“触发事件（Trigger Events）”。
- 生成**疗愈相册**与**探索报告**，将用户的心理成长轨迹可视化。

---

## 3. 技术亮点 (Technical Highlights)

### 3.1 多智能体协同架构 (Multi-Agent Collaboration)
系统打破了单一 LLM 的对话模式，构建了复杂的 Agent 协作网络：
- **Manager Agent**：负责与用户直接交互，维持对话温度。
- **Counselor Agent**：在后台进行深度的心理学分析，提取结构化数据（JSON）。
- **Sub-persona Agents**：在议会模式下自主辩论，模拟真实的心理冲突。

### 3.2 情绪驱动的状态机 (Emotion-Driven State Machine)
- 自研 `PersonaStateMachine`，通过计算情绪强度（Intensity）和衰减率（Decay Rate），实现人格状态的自然平滑过渡。
- 避免了生硬的规则切换，使得 AI 的表现更接近真实人类的心理波动。

### 3.3 基于 RAG 的长效心理记忆 (RAG-based Long-term Memory)
- 结合 **ChromaDB** 向量数据库与 **SentenceTransformer** 嵌入模型，实现长效记忆。
- 不仅检索对话历史，更侧重于检索用户的“核心信念”和“历史创伤事件”，使得 AI 能够提供具有深度连贯性的心理咨询体验。

### 3.4 WebGL 沉浸式视觉体验 (WebGL Immersive Visuals)
- 前端采用 **Three.js** 编写自定义 Shader（着色器），实现流体背景（ShaderBackground）。
- 背景的颜色、流速和粒子效果会根据当前活跃的人格（Manager/Exiles/Firefighters）和情绪强度实时变化，提供极致的沉浸感（Glassmorphism 毛玻璃 UI 风格）。

---

## 4. 技术方案特色 (Technical Solution Features)

### 4.1 架构选型
- **前端 (Frontend)**：Vue 3 (Composition API) + Vite + Vuetify + Pinia + Three.js。采用响应式设计，完美适配移动端与桌面端。
- **后端 (Backend)**：FastAPI + SQLAlchemy (Async) + SQLite/PostgreSQL。全异步非阻塞架构，保障高并发下的响应速度。
- **大模型接入**：对接阿里云 DashScope API，并设计了多层 Prompt 模板与 JSON 格式自动修复（Fallback/Repair）机制，确保 Counselor 分析结果的稳定性。

### 4.2 性能与体验优化
- **SSE (Server-Sent Events) 流式输出**：在内心议会和长对话中采用 SSE 技术，实现打字机效果，消除用户等待焦虑。
- **后台任务 (Background Tasks)**：将耗时的 RAG 向量化存储、心理报告生成等操作放入 FastAPI 的后台任务中执行，确保主对话接口的毫秒级响应。
- **智能模型加载策略**：Embedding 模型支持本地缓存、ModelScope 和 HuggingFace Mirror 三级降级加载策略，适应各种复杂的部署网络环境。

### 4.3 自动化运维与自愈 (Auto-healing & DevOps)
- 包含独立的 `autoheal` 智能体框架，能够自动检测宿主机环境（Python, Docker）、安装依赖并启动 Docker Compose 容器集群。
- 具备服务健康检查与自动恢复能力，极大降低了项目的部署与维护门槛。