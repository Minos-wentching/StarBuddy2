# Trauma Event 全局重构规范（冻结版）

更新时间：2026-02-23

## 0. 迁移进度（实时）

状态定义：
- ✅ 已完成
- 🟡 进行中
- ⏳ 未开始

当前状态（2026-02-23）：

- ✅ Phase A / 兼容读写（后端）
  - `ifs_onboarding` 已支持 `trauma_events_*` 与 `memory_orbs_*` 双写兼容
  - 归档与恢复链路已保留并恢复 `trauma_events_*` 与旧字段镜像
- ✅ Phase A / 兼容读写（前端）
  - 读取优先 `trauma_events_*`，缺失时回退 `memory_orbs_*`
  - 自定义事件写入已双写（新旧字段）
- ✅ Session `event_context` 基础落地
  - onboarding parse / restore 已初始化 `event_context`
  - 日记生成后会回写 `active_event_*` 与 `event_history`
- ✅ 日记小日志（观测）
  - 已记录 `source/level/event_preview/belief_count`（服务日志）
- 🟡 Phase B / 历史数据回填脚本
  - 规范已定义，回填脚本已就绪：`scripts/migrate_trauma_events.py`
  - 已改为“同步 SQL + 直连 users 表”模式，避免运行时触发 async DB 依赖
  - 待在目标环境执行（建议先 `--dry-run`）并记录 `scanned/changed`
- ⏳ Phase C / 停写旧字段与清理回退代码

目标：将“记忆球”语义统一为 `trauma_event`，形成两条清晰数据线：
- 具体事件线：`trigger_events` / `trauma_events`
- 抽象认知线：`core_beliefs`

并确保：
- 记忆球 UI 只反映“具体事件”；
- 日记生成以“具体事件”为锚点；
- 两者都能吃到抽象上下文（核心信念与画像摘要）。

---

## 1. 术语与边界

- `trigger_event`：当前轮次触发点（短时态、会话内）
- `trauma_event`：用户相对稳定/可复用的关键事件记忆（可长期保留）
- `core_belief`：抽象信念（解释层）

原则：
- 具体事件和抽象信念分层存储，不混同字段。
- UI（记忆球）展示具体事件，不直接展示抽象信念。
- 生成（如日记）以具体事件做主锚点，抽象信念只作为上下文辅助。

---

## 2. 字段字典（目标态）

### 2.1 User.settings.ifs_onboarding（长期画像）

新增/标准化字段：

- `trauma_events_fixed: TraumaEvent[]`
  - 首次问卷解析后生成，一经确认保持稳定（可版本化回溯）
- `trauma_events_custom: TraumaEvent[]`
  - 用户手动维护的具体事件
- `trauma_events_initialized: bool`
  - 具体事件是否已完成初始化

保留字段（抽象层）：
- `core_beliefs: string[]`
- `profile_digest: string`
- `persona_portraits: { exiles: string, firefighters: string }`
- `profile_version: number`
- `profile_confirmed: bool`

`TraumaEvent` 结构：

```json
{
  "event_id": "string",
  "title": "string",
  "trigger_event": "string",
  "trauma_event": "string",
  "intensity": 0.0,
  "persona_hint": "exiles|firefighters|manager",
  "source_type": "onboarding_fixed|custom|memory_extract|manual",
  "created_at": "ISO8601",
  "updated_at": "ISO8601",
  "event_rank": 1
}
```

### 2.2 Session.persona_state（会话态）

新增/标准化字段：

- `event_context: { ... }`
  - `active_event_id`
  - `active_trigger_event`
  - `active_trauma_event`
  - `active_event_source`
  - `event_history: EventRef[]`（可选）

保留字段（抽象上下文）：
- `onboarding_profile.core_beliefs`
- `onboarding_profile.profile_digest`

### 2.3 Chroma Metadata（向量记忆）

新增类型：

- `type = "trauma_event"`
  - metadata: `event_id`, `trigger_event`, `trauma_event`, `source_type`, `intensity`, `user_id`, `timestamp`
- `type = "core_belief"`（保留）
  - metadata: `belief_id`, `trigger`, `valence`, `intensity`, `user_id`, `timestamp`

要求：
- `trauma_event` 与 `core_belief` 双通道写入。
- 读取时可按 `type` 精确过滤，不再依赖文本文案解析。

---

## 3. 旧字段 → 新字段映射（兼容期）

### 3.1 前端/用户设置

- `memory_orbs_fixed` → `trauma_events_fixed`
- `memory_orbs_custom` → `trauma_events_custom`
- `memory_orbs_initialized` → `trauma_events_initialized`

对象字段映射：

- `id` → `event_id`
- `trauma_text`/`traumaText` → `trauma_event`
- `trigger_event`/`triggerEvent` → `trigger_event`
- `orb_rank`/`orbRank` → `event_rank`

### 3.2 会话态

- `lastCouncilTopic`（前端）→ `event_context.active_trigger_event`
- `selectedOrbId`（前端）→ `event_context.active_event_id`

### 3.3 日记输入优先级（目标态）

1. `event_context.active_trauma_event`（会话当前激活事件）
2. `trauma_event` 检索命中（Chroma type=trauma_event）
3. `manager_decision.events`
4. `counselor_report.trigger_event`
5. 用户原话截取
6. 默认回退

---

## 4. 数据流（目标态）

### 4.1 写入流

1) 用户输入 → Counselor
- 产出 `core_beliefs[]`（抽象）和 `trigger_event`（具体）

2) MemoryStore 写入
- 写 `trauma_event` 文档（具体）
- 写 `core_belief` 文档（抽象）

3) Manager 决策
- 可附加 `events`，用于会话内候选补充

4) 事件激活（记忆球点击/自动选中）
- 更新 `Session.persona_state.event_context`

5) 日记生成
- 读取优先级链路选出具体事件锚点
- 同时注入 `core_beliefs + profile_digest + rag_context` 作为抽象上下文

### 4.2 读取流

- 记忆球列表：只读 `trauma_events_fixed + trauma_events_custom`（兼容期支持旧字段回退）
- 报告/分析：可同时展示事件层和信念层，但视觉上分区
- 日记：事件锚点 + 抽象上下文并行输入

---

## 5. 迁移方案（分阶段）

### Phase A（兼容读，不破坏）

- 所有读取逻辑先读新字段：`trauma_events_*`
- 若缺失，回退旧字段：`memory_orbs_*`
- 写入暂时双写（新旧都写）

### Phase B（回填）

- 一次性脚本遍历 `User.settings`
  - 将 `memory_orbs_*` 映射为 `trauma_events_*`
  - 补齐 `event_id/event_rank/updated_at`
- Chroma 回填 `type=trauma_event`（可从既有 core_belief 文本解析 trigger/origin）

### Phase C（切换）

- 前后端停止写旧字段，仅保留新字段
- 监控 1-2 个迭代周期后，移除旧字段回退代码

---

## 6. 观测日志（小日志）

日记生成记录字段：

- `diary_event_source`
- `diary_event_id`
- `diary_event_text_preview`
- `diary_fallback_level`（1-6）
- `diary_context_belief_count`

目的：验证“具体事件优先级”是否按预期命中。

---

## 7. 验收标准（Definition of Done）

1) 记忆球 UI 不再直接使用抽象信念作为球体内容。
2) 日记文本可追溯到具体事件来源（日志可见）。
3) `core_beliefs` 仍完整参与上下文推理。
4) 老用户数据无损可读，迁移后行为一致或更优。
5) 回滚/恢复人格档案不破坏 `trauma_events` 与 `core_beliefs`。

---

## 8. 实施顺序（建议）

1. 后端 schema 与读写兼容层（新字段 + 回退）
2. MemoryStore 双写与 `type=trauma_event` 查询能力
3. DialogueService 事件优先级改造（先 session event_context，再 memory）
4. 前端记忆球数据源切换（`trauma_events_*`）
5. 回填脚本执行与观测日志上线
6. 清理旧字段写入
