---
domain:
tags:
  - 孤独症
  - 多智能体
  - 心理辅助
datasets:
  evaluation:
  test:
  train:
models:
license: Apache License 2.0
---

# 星伴 StarBuddy

面向孤独症谱系人群的多智能体辅助对话系统。通过模拟内心不同"伙伴"之间的协作与对话，帮助用户理解自身的感知方式、情绪模式和行为习惯，在安全、可预测的环境中建立自我认知。

## 核心理念

每个人的内心都有不同的声音。星伴将这些声音具象化为四个伙伴：

| 伙伴 | 角色 | 说明 |
|------|------|------|
| 安全岛 (Safe Island) | 主对话伙伴 | 稳定、可预测的交流基地，提供安全感 |
| 感知精灵 (Sensory Sprite) | 感官敏感的自我 | 感官过载、情绪波动时激活 |
| 规则守卫 (Rule Guardian) | 秩序的守护者 | 面对变化和不确定性时激活 |
| 星星向导 (Star Guide) | 后台分析师 | 分析行为模式，帮助建立自我认知 |

系统根据对话中的情绪强度自动切换伙伴，当感知精灵与规则守卫产生冲突时，会触发「星球会议」进行多轮协商，最终由星星向导总结行为模式，生成「内心星图」。

## 功能模块

- 多伙伴实时对话 — SSE 流式响应，伙伴根据情绪状态自动切换
- 星球会议 — 感知精灵与规则守卫的多轮对话协商
- 内心星图 — 核心行为模式的识别与追踪
- 感知画册 — AI 生成的意象图片日记
- 星际连线 — 漂流瓶社交，与相似用户建立连接
- 成长报告 — 可视化的情绪轨迹与成长分析
- 会话快照 — 状态版本管理与回溯

## 技术架构

```
┌─────────────────────────────────────────────┐
│                   Nginx :7860                │
│         静态资源 + /api 反向代理              │
├──────────────────┬──────────────────────────┤
│   Vue 3 前端      │     FastAPI 后端 :8000    │
│                  │                          │
│  Vuetify 3       │  多 Agent 调度            │
│  Pinia 状态管理   │  Persona 状态机           │
│  Three.js 背景   │  情绪分析引擎             │
│  SSE 实时通信     │  ChromaDB 向量记忆        │
│                  │  SQLite 持久化            │
│                  │  DashScope LLM           │
└──────────────────┴──────────────────────────┘
```

### 后端

- Python 3.11 / FastAPI / Uvicorn
- SQLAlchemy 2.0 (async) + aiosqlite
- ChromaDB + sentence-transformers — RAG 记忆检索
- DashScope API — qwen-max (对话) / qwen-plus (情绪分析) / z-image-turbo (图片生成)
- SSE 实时事件推送（伙伴切换、会议进度、日记生成）
- JWT 认证

### 前端

- Vue 3.4 / Vite 5
- Vuetify 3 + Tailwind CSS 4
- Pinia 状态管理
- Three.js WebGL 动态背景
- Axios + SSE 客户端

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- DashScope API Key（[申请地址](https://dashscope.console.aliyun.com/)）

### 方式一：Docker Compose（推荐）

```bash
# 1. 克隆项目
git clone https://www.modelscope.cn/studios/zhupeiling/MultiMe_IFS.git
cd MultiMe_IFS

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env，填入 DASHSCOPE_API_KEY

# 3. 启动
docker compose up
```

访问 http://localhost:5173（前端）/ http://localhost:8000（API）

### 方式二：本地开发

```bash
# 后端
pip install -r requirements.txt
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload

# 前端（另一个终端）
cd frontend
npm install
npm run dev
```

### 环境变量

| 变量 | 说明 | 必填 |
|------|------|------|
| `DASHSCOPE_API_KEY` | 阿里云 DashScope API 密钥 | 是 |
| `JWT_SECRET_KEY` | JWT 签名密钥（不设则自动生成） | 否 |
| `DATABASE_URL` | 数据库连接串，默认 SQLite | 否 |
| `ENVIRONMENT` | `development` / `production` | 否 |
| `ALLOWED_ORIGINS` | CORS 允许的源，逗号分隔 | 否 |

## 项目结构

```
├── backend/
│   ├── main.py                 # FastAPI 入口
│   ├── api_config.py           # 集中配置
│   ├── api/                    # API 端点 (auth/dialogue/council/sse/social/images/version)
│   ├── core/                   # 状态机 + 情绪分析
│   ├── services/               # 业务逻辑 + LLM Prompt
│   ├── database/               # ORM 模型
│   └── auth/                   # JWT 认证
├── frontend/
│   ├── src/
│   │   ├── views/              # 页面 (Home/Council/Report/Social/...)
│   │   ├── components/         # 组件 (CouncilDebateLog/ShaderBackground/...)
│   │   ├── stores/             # Pinia 状态
│   │   ├── composables/        # SSE/Persona 组合式函数
│   │   └── design-system/      # 设计令牌
│   └── index.html
├── docker-compose.yml          # 本地开发
├── Dockerfile                  # 生产构建
├── nginx.conf                  # 生产反向代理
└── start.sh                    # 生产启动脚本
```

## 部署

项目支持部署到 [ModelScope 创空间](https://modelscope.cn/studios)，使用多阶段 Docker 构建：

```bash
# 构建生产镜像
docker build -t starbuddy .

# 运行（端口 7860）
docker run -p 7860:7860 --env-file .env starbuddy
```

生产环境通过 Nginx 统一暴露 7860 端口，静态资源直接服务，API 请求代理到后端 8000 端口。

## 许可证

[Apache License 2.0](LICENSE)
