# 多阶段构建 Dockerfile

# 第一阶段: 构建前端
FROM node:18-alpine as frontend-builder

WORKDIR /app/frontend

# 复制前端依赖文件
COPY frontend/package*.json ./

# 安装所有依赖（包括开发依赖）
RUN npm config set registry https://registry.npmmirror.com && \
    npm install --production=false && npm cache clean --force

# 确保vite可执行文件存在并调试
RUN echo "当前目录: $(pwd)" && \
    ls -la node_modules/.bin/vite 2>/dev/null || echo "node_modules/.bin/vite not found" && \
    ls -la node_modules/vite/bin/vite.js 2>/dev/null || echo "node_modules/vite/bin/vite.js not found" && \
    node --version && npm --version

# 复制前端源代码
COPY frontend/ .

# 构建前端（设置内存限制）- 使用npm run build
RUN echo "构建前检查:" && \
    pwd && \
    ls -la node_modules/.bin/ | grep vite && \
    NODE_OPTIONS="--max-old-space-size=1024" npm run build

# 第二阶段: 构建后端
FROM python:3.11-slim

WORKDIR /app

# 安装最小系统依赖（分开执行以减少内存使用）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update && \
    apt-get install -y --no-install-recommends nginx curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*

# 复制后端依赖文件
COPY requirements.txt .

# 安装Python依赖（使用缓存优化）
RUN pip install --no-cache-dir -r requirements.txt
# 修复chromadb与numpy 2.0的兼容性问题
RUN find /usr/local/lib -name "types.py" -path "*/chromadb/api/types.py" -exec sed -i 's/np\.float_/np.float64/g' {} \;

# 复制后端源代码
COPY backend/ ./backend

# 复制前端构建结果
COPY --from=frontend-builder /app/frontend/dist ./frontend/dist

# 复制nginx配置和启动脚本
COPY nginx.conf /app/nginx.conf
COPY start.sh /app/start.sh

# 设置执行权限
RUN chmod +x /app/start.sh

# 创建非root用户（必须先创建用户，后面才能使用）
RUN useradd -m -u 1000 appuser

# 创建必要的目录并设置权限
RUN mkdir -p /app/data /app/run /app/chroma_storage \
    && chown -R appuser:appuser /app/data /app/run /app/chroma_storage

# 设置 /app 目录权限
RUN chown -R appuser:appuser /app

# 创建Nginx需要的目录并设置权限
RUN mkdir -p /var/lib/nginx /var/log/nginx /var/cache/nginx /run/nginx /app/run \
    && chown -R appuser:appuser /var/lib/nginx /var/log/nginx /var/cache/nginx /run/nginx /app/run \
    && chmod -R 755 /var/lib/nginx /var/log/nginx /var/cache/nginx /run/nginx /app/run

USER appuser

# 暴露端口 (魔塔要求7860)
EXPOSE 7860

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["/app/start.sh"]