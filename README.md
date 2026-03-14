# StarBuddy2（星伴）

一个面向**孤独症谱系用户**的情绪释放与沟通辅助平台，同时为**监护人**提供观察、整理与理解的能力。当前版本在同一套前端里支持两种“端角色”：**用户端（孤独症患者端）**与**监护人端**。

## 两端入口（重要）

- 打开前端地址后会先进入 `/entry`：选择 **监护人端 / 用户端**。
- 监护人端：继续使用原来的 `/login` 登录界面（UI 不变）。
- 用户端：进入全屏深蓝引导 UI（无需登录也可使用本地模式；登录后可同步到账号）。

> 注意：这是“两个端（角色）”，不是两个前端端口；默认仍是一个前端端口（5173）。

## 功能概览

### 用户端（孤独症患者端）
- 新的全屏引导流程：**你叫什么名字 → 深呼吸 → 指令循环**（固定底部两按钮：灰=深呼吸，黑=继续）。
- 保留并可从菜单进入：**安全岛**（`/immersive`）、**拾一封信**（漂流瓶页：`/social?tab=bottle&action=pick`）。

### 监护人端
- 保留原有功能入口：感知画册、会议记录、更多选项、成长报告、看我的星图、记忆中枢等。
- 在“设置”页新增：**用户端设置**（可编辑用户端指令列表、背景色与缓慢变色，并同步到后端）。

## 交互性技术文档

请见：`docs/interaction_technical_documentation.md`

## 开发运行（PowerShell）

### 环境要求
- Windows + PowerShell
- Python 3.11+
- Node.js 18+（含 npm）

### 1）启动后端（FastAPI）
在仓库根目录打开 PowerShell：

```powershell
cd D:\StarBuddy2\StarBuddy

# (可选) 建议使用虚拟环境
python -m venv .venv
.\.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# 允许前端跨域（开发时建议设置）
$env:ENVIRONMENT="development"
$env:ALLOWED_ORIGINS="http://127.0.0.1:5173,http://localhost:5173"

uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

后端文档：`http://127.0.0.1:8000/docs`

> 首次启动可能会下载/初始化 embedding 模型与向量存储，耗时较长属正常现象。

### 2）启动前端（Vite）
另开一个 PowerShell：

```powershell
cd D:\StarBuddy2\StarBuddy\frontend
npm install

# 让 Vite 代理把 /api 转发到后端
$env:VITE_PROXY_TARGET="http://127.0.0.1:8000"

npm run dev -- --host 127.0.0.1 --port 5173
```

打开：`http://127.0.0.1:5173/` → 自动进入 `/entry` 选择端角色。

### 常见问题
- **8000 端口被占用**：把后端改成 8001，并同步改前端代理：
  - 后端：`--port 8001`
  - 前端：`$env:VITE_PROXY_TARGET="http://127.0.0.1:8001"`
- **想重新选择端角色**：清空浏览器 localStorage 的 `app_role`（或换无痕窗口）。

### 本地免费 AI（可选，推荐 Ollama）
如果你不配置 `DASHSCOPE_API_KEY`，后端会优先尝试使用本地 Ollama（若可用），否则退回到“非固定”的降级回复。

```powershell
$env:LOCAL_LLM_PROVIDER="ollama"
$env:OLLAMA_BASE_URL="http://127.0.0.1:11434"
$env:OLLAMA_MODEL="qwen2.5:7b"
```

### 放置文献（可选）
把你希望 AI 参考的资料放到 `references/`（建议 `.txt/.md`），后端会做轻量关键词摘录并注入对话上下文。

## Docker Compose（可选）
在仓库根目录：

```powershell
cd D:\StarBuddy2\StarBuddy
docker compose up --build
```

前端：`http://127.0.0.1:5173/`

## 许可证
[Apache License 2.0](LICENSE)
