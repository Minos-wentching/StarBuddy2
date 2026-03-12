# SKILL.md — 项目启动与自动运维技能

> 本文件定义 Claude 在需要 **启动项目、监控容器、自动修复错误** 时应遵循的完整操作流程。
> 交互逻辑参考 `启动超级管理员.sh` + `autoheal/agent.py` Butler 模式。

---

## 1. 前置环境检查

在启动项目前，**必须按顺序**验证以下依赖：

### 1.1 检查 Python3
```bash
python3 --version
# Windows 替代：python --version
```
如果不可用，提示用户安装 Python 3.11+。

### 1.2 检查 Docker
```bash
docker --version
```
如果未安装，提示用户安装 Docker Desktop。

### 1.3 检查 Docker 守护进程是否运行
```bash
docker ps
```
- 如果 Docker 未运行（命令报错），尝试启动：
  - Linux/WSL: `sudo service docker start`
  - Windows: 提示用户打开 Docker Desktop
- 启动后最多重试 **5 次**，每次间隔 **3 秒**，验证 `docker ps` 是否成功
- 超过 5 次仍失败，报告错误并停止

### 1.4 检查 Docker Compose
按优先级检测可用命令：
```bash
# 优先检查独立命令
docker-compose version
# 其次检查插件形式
docker compose version
```
记住检测到的命令（后续统一使用），两者都不可用则报告错误。

### 1.5 检查依赖文件
确认项目根目录存在以下文件：
- `requirements.txt` — Python 后端依赖
- `docker-compose.yml` — 容器编排配置
- `Dockerfile.backend.dev` — 后端开发镜像
- `Dockerfile.frontend.dev` — 前端开发镜像

---

## 2. 启动容器

### 2.1 安装宿主机 Python 依赖
autoheal 需要在宿主机运行，因此先安装依赖。

**必须使用虚拟环境**（系统 Python 启用了 PEP 668 保护，直接 pip install 会被拒绝）：
```bash
# 如果虚拟环境不存在，先创建
python3 -m venv .venv

# 使用虚拟环境的 pip 安装（无需 activate）
.venv/bin/pip install -r requirements.txt

# 或者先激活再安装
source .venv/bin/activate
pip install -r requirements.txt
```
> **注意**: requirements.txt 包含 torch、nvidia-* 等大包，首次安装下载量较大（约 5GB+），请耐心等待。

### 2.2 构建并启动容器
在项目根目录执行：
```bash
docker compose up -d --build
```
这会启动两个服务：
| 服务 | 端口 | 说明 |
|------|------|------|
| backend | 8000 | FastAPI 后端 (uvicorn --reload) |
| frontend | 5173 | Vue.js 前端 (Vite dev server) |

**关键特性**：
- 后端使用 `volume mount` 挂载 `./backend` → `/app/backend`，配合 `uvicorn --reload`，宿主机改代码后容器自动重载
- 前端使用 `volume mount` 挂载 `./frontend` → `/app/frontend`，Vite HMR 自动生效
- 数据持久化：`./data` → `/app/data` (SQLite), `./chroma_storage` → `/app/chroma_storage` (ChromaDB)

### 2.3 验证容器状态
```bash
docker compose ps
```
确认两个容器均处于 `running` 状态。

---

## 3. 健康检查

启动容器后，**必须**轮询健康检查端点确认后端就绪：

```
GET http://localhost:8000/health
```

**轮询策略**：
- 超时上限: **60 秒**
- 轮询间隔: **3 秒**
- 成功条件: HTTP 200
- 超时处理: 打印 `docker compose ps` + `docker compose logs backend --tail=50` 帮助诊断

**修复后二次验证**（修改代码后等 uvicorn reload）：
- 等待 **4 秒** 让 uvicorn 完成重载
- 轮询上限缩短为 **20 秒**，间隔 **2 秒**

---

## 4. 错误监控

### 4.1 监控方式
通过 Docker SDK 实时监听 backend 容器日志流：
```bash
# 命令行等价操作（实际使用 Docker SDK）
docker logs -f <backend_container_name>
```

### 4.2 容器名称自动检测
按以下优先级检测 backend 容器：
1. 容器名包含 `backend` 的
2. 容器名包含 `app` 的
3. 第一个运行中的容器

### 4.3 错误模式匹配
使用正则表达式检测以下错误类型（按严重程度排列）：

| 错误类型 | 正则模式 | 严重程度 |
|----------|----------|----------|
| TRACEBACK | `Traceback.*` | HIGH |
| SYNTAX_ERROR | `SyntaxError.*` | HIGH |
| IMPORT_ERROR | `ImportError.*` | HIGH |
| MODULE_NOT_FOUND | `ModuleNotFoundError.*` | HIGH |
| NAME_ERROR | `NameError.*` | MEDIUM |
| TYPE_ERROR | `TypeError.*` | MEDIUM |
| VALUE_ERROR | `ValueError.*` | MEDIUM |
| ATTRIBUTE_ERROR | `AttributeError.*` | MEDIUM |
| KEY_ERROR | `KeyError.*` | MEDIUM |
| INDEX_ERROR | `IndexError.*` | MEDIUM |
| FILE_NOT_FOUND | `FileNotFoundError.*` | HIGH |
| PERMISSION_ERROR | `PermissionError.*` | HIGH |
| CONNECTION_ERROR | `ConnectionError.*` | MEDIUM |
| TIMEOUT_ERROR | `TimeoutError.*` | MEDIUM |
| ERROR_LOG | `ERROR\s.*` | MEDIUM |
| EXCEPTION | `Exception.*` | HIGH |

### 4.4 冷却机制
- 同类错误在 **60 秒内**不重复处理（防止修复循环）
- 每小时最多处理 **10 个错误**

---

## 5. 错误修复链路

检测到错误后，按 **三层策略链** 逐级升级修复：

```
第一层: 内置策略 (快速、确定性修复)
    ↓ 失败
第二层: Gemini CLI (AI 分析修复)
    ↓ 失败
第三层: Claude Code CLI (终极兜底)
```

### 5.1 内置策略（第一层）

#### ImportError / ModuleNotFoundError
- 用正则提取缺失模块名: `No module named '([^']+)'`
- 取顶层包名（如 `a.b.c` → `a`）
- 排除标准库模块，对第三方包执行 `pip install <module>`
- 超时限制: 120 秒

#### SyntaxError
- 从错误信息提取文件路径和行号
- **先备份**源文件 (`<file>.backup`)
- 自动修复类型:
  - 缺少冒号: 行尾补 `:`
  - 未闭合括号: 行尾补 `)`
  - 未闭合字符串: 行尾补引号
  - 缩进错误: 对齐前一行缩进
- 修复后用 `compile()` 验证语法正确性

#### FileNotFoundError
- 提取缺失文件路径
- 自动创建父目录
- 对配置文件 (`.env`, `.json`, `.yaml` 等) 生成模板内容
- 其他文件创建空文件

### 5.2 Gemini CLI（第二层）
```bash
gemini -p "<修复 prompt>"
```
- 超时: 300 秒
- 实时打印 AI 思维链输出
- 工作目录: 项目根目录

### 5.3 Claude Code CLI（第三层 — 终极兜底）
```bash
claude --print --dangerously-skip-permissions -p "<修复 prompt>"
```
- 超时: 300 秒
- 需要的环境变量:
  - `ANTHROPIC_BASE_URL`
  - `ANTHROPIC_AUTH_TOKEN`
  - `ANTHROPIC_MODEL`
  - `ANTHROPIC_SMALL_FAST_MODEL`
- 实时打印 AI 思维链输出
- 工作目录: 项目根目录

### 5.4 修复 Prompt 模板
```
你是一个自动修复 agent。后端容器日志中检测到以下错误，请直接修复源码。

错误类型: {error_type}
错误信息: {error_message}
文件路径: {file_path}（如有）
行号: {line_number}（如有）

请分析错误原因，找到对应的源码文件并直接修复。
源码在当前目录的 backend/ 下。
只修改必要的代码，不要做多余的重构。
修复完成后简要说明你做了什么。
```

### 5.5 修复后验证
每次修复后：
1. 等待 4 秒让 uvicorn reload
2. 调用健康检查 `GET http://localhost:8000/health`（超时 20 秒）
3. 继续监控容器日志确认错误不再出现

---

## 6. 停止服务

```bash
docker compose down
```
这会停止并移除所有容器。数据卷中的数据 (SQLite, ChromaDB) 保留在宿主机。

如果只想停止监控但保持容器运行，直接停止 autoheal 进程即可（Ctrl+C 或终止任务）。

---

## 7. 一键操作命令（使用 autoheal 模块）

如果宿主机环境已配置好，可以直接调用 autoheal 模块：

```bash
# 一键启动容器 + 监控 + 自动修复（等价于启动超级管理员.sh）
python -m autoheal butler

# 停止所有容器
python -m autoheal butler --down

# 仅启动监控（不启动容器，前台运行）
python -m autoheal start

# 查看监控状态
python -m autoheal status

# 查看修复报告
python -m autoheal report --hours 24

# 查看配置
python -m autoheal config
```

---

## 8. 关键文件索引

### 基础设施
| 文件 | 说明 |
|------|------|
| `docker-compose.yml` | 容器编排（backend:8000, frontend:5173） |
| `Dockerfile.backend.dev` | 后端开发镜像 (Python 3.11) |
| `Dockerfile.frontend.dev` | 前端开发镜像 (Node 18) |
| `requirements.txt` | Python 依赖 |
| `.env` | 环境变量（API 密钥等） |

### 后端核心
| 文件 | 说明 |
|------|------|
| `backend/main.py` | FastAPI 入口 |
| `backend/api_config.py` | API 配置加载 |
| `backend/services/dialogue_service.py` | 对话服务（核心业务逻辑） |
| `backend/services/council_service.py` | 议会辩论服务 |
| `backend/services/counselor_service.py` | 咨询师 / 核心信念服务 |
| `backend/services/memory_service.py` | ChromaDB 记忆检索 |
| `backend/services/external_apis.py` | DashScope API 调用 |
| `backend/services/prompts.py` | Persona 提示词 |
| `backend/database/models.py` | SQLAlchemy 数据模型 |
| `backend/database/database.py` | 数据库连接 |

### 前端
| 文件 | 说明 |
|------|------|
| `frontend/src/App.vue` | 根组件 |
| `frontend/src/main.js` | 入口 |
| `frontend/vite.config.js` | Vite 配置 |

### 自动修复系统
| 文件 | 说明 |
|------|------|
| `autoheal/__main__.py` | CLI 入口 |
| `autoheal/agent.py` | Agent 主体 + Butler 管家模式 |
| `autoheal/strategies.py` | 三层修复策略 |
| `autoheal/config.py` | 配置管理 |
| `autoheal/dashboard.py` | 监控仪表板 |
| `error_patterns.json` | 错误模式定义 |

---

## 9. 标准交互流程

### 用户说"启动项目" / "跑起来" / "launch"
执行完整流程：
1. 前置检查 (§1)
2. 启动容器 (§2)
3. 健康检查 (§3)
4. 报告访问地址:
   - 后端 API: http://localhost:8000
   - API 文档: http://localhost:8000/docs
   - 前端页面: http://localhost:5173
5. 开始监控日志 (§4)，检测到错误自动修复 (§5)

### 用户说"停止" / "关掉" / "stop"
```bash
docker compose down
```

### 用户说"状态" / "怎么样了"
```bash
docker compose ps
# + 健康检查
curl http://localhost:8000/health
```

### 用户说"日志" / "报错了"
```bash
docker compose logs backend --tail=100
# 分析最近的错误并尝试修复
```

### 用户说"重启后端"
```bash
docker compose restart backend
# 等待健康检查通过
```

---

## 10. 注意事项

1. **代码热重载**: 后端使用 `uvicorn --reload`，前端使用 Vite HMR。修改宿主机源码后容器自动生效，**不需要重新构建镜像**。只有修改 `requirements.txt` 或 `package.json` 时才需要 `docker compose up -d --build`。

2. **API 密钥**: 所有 DashScope 服务统一使用 `DASHSCOPE_API_KEY` 环境变量，配置在 `.env` 文件中。

3. **数据库**: SQLite 文件在 `./data/inner_mirror.db`，ChromaDB 在 `./chroma_storage/`。这些通过 volume mount 持久化在宿主机，容器重建不会丢失数据。

4. **Windows 环境**: 
   - Docker 命令使用 `docker compose`（空格分隔，不是连字符）
   - 路径使用反斜杠或正斜杠均可
   - 确保 Docker Desktop 已启动

5. **修复安全边界**:
   - 只允许修改 `backend/`、`frontend/` 目录下的文件
   - 禁止修改 `.env`、`secrets`、`credentials` 等敏感文件
   - 修复前自动备份原文件
   - 单个文件最大修改限制 1024KB

6. **错误处理原则**: 不要一次改太多。定位到具体错误文件和行号，做最小化修复，改完等 reload 验证通过再处理下一个错误。

## 11. 故障排除

### WSL2 Docker Desktop 挂载错误

**症状**: 启动 backend 容器时出现错误:
```
Error response from daemon: error while creating mount source path '/run/desktop/mnt/host/wsl/docker-desktop-bind-mounts/Ubuntu/...': mkdir ...: file exists
```

**原因**: WSL2 与 Docker Desktop 的挂载路径缓存冲突，常见于容器频繁重建的场景。

**解决方案**:
1. **临时方案**: 直接运行容器，不挂载 volume（仅测试）:
   ```bash
   docker run -d --name test-backend -p 8000:8000 \
     -e DATABASE_URL=sqlite:///./data/inner_mirror.db \
     -e CHROMA_PERSIST_DIR=/app/chroma_storage \
     -e ALLOWED_ORIGINS=http://localhost:5173,http://localhost:8000 \
     test-backend \
     uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```
2. **永久方案**:
   - 重启 Docker Desktop
   - 清理 Docker 系统: `docker system prune -a` (注意: 会删除所有镜像和容器)
   - 重启 WSL2: `wsl --shutdown` 然后重新启动
   - 检查宿主目录权限，确保 `./data` 和 `./chroma_storage` 目录存在且可写

### 宿主机 Python 依赖安装被阻止

**症状**: `pip install -r requirements.txt` 失败，提示 `externally-managed-environment`

**原因**: 系统 Python 启用了 PEP 668 保护，禁止直接安装包。

**解决方案**:
1. 使用项目已有的虚拟环境: `.venv/bin/pip install -r requirements.txt`
2. 如果虚拟环境不存在，创建新的: `python3 -m venv .venv`
3. 激活虚拟环境: `source .venv/bin/activate`

### 健康检查显示数据库连接失败

**症状**: `GET /health` 返回 `{"status":"degraded","checks":{"database":false}}`

**原因**: SQLite 数据库文件不存在或容器内无写入权限。

**解决方案**:
1. 确保 `./data` 目录存在且容器可写
2. 首次启动时，数据库会自动创建
3. 检查 volume mount 是否正确映射

### 快速验证容器是否正常

如果 docker compose 因挂载问题失败，可分别验证:
1. **前端**: `docker compose up -d frontend`，访问 http://localhost:5173
2. **后端**: 使用上述临时方案运行 backend 容器，验证 http://localhost:8000/health 返回 200

### 自动修复系统依赖

autoheal 模块需要宿主机安装 Python 依赖。如果 `python -m autoheal` 失败，确保:
1. 虚拟环境已激活
2. 已安装 `requirements.txt` 中的所有包
3. Docker SDK (docker-py) 版本兼容
