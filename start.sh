#!/bin/bash

# 启动脚本：同时启动FastAPI后端和nginx

# 设置环境变量
export PYTHONPATH=/app
export PYTHONUNBUFFERED=1

# 确保ENVIRONMENT变量有值（默认production）
if [ -z "$ENVIRONMENT" ]; then
    export ENVIRONMENT="production"
fi

echo "=== 启动配置 ==="
echo "环境: $ENVIRONMENT"
echo "工作目录: $(pwd)"
echo "Python路径: $PYTHONPATH"
echo "用户: $(whoami)"
echo "UID: $(id -u)"
echo "GID: $(id -g)"

# 检查Nginx所需目录权限
echo "检查Nginx目录权限..."
nginx_dirs="/var/lib/nginx /var/log/nginx /var/cache/nginx /run/nginx /app/run /app/data"
for dir in $nginx_dirs; do
    if [ ! -d "$dir" ]; then
        echo "警告: 目录 $dir 不存在，尝试创建..."
        mkdir -p "$dir" 2>/dev/null || echo "无法创建目录 $dir，继续..."
    fi
    if [ ! -w "$dir" ]; then
        echo "警告: 目录 $dir 不可写，尝试修改权限..."
        chmod 755 "$dir" 2>/dev/null || true
    fi
done

# 启动FastAPI后端（在后台运行）
echo "启动FastAPI后端..."
cd /app
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --access-log &
BACKEND_PID=$!

# 等待后端启动
echo "等待FastAPI后端启动..."
sleep 10

# 检查后端健康状态，最多重试5次
echo "检查后端健康状态..."
MAX_RETRIES=5
RETRY_DELAY=2
HEALTH_CHECK_SUCCESS=false

for i in $(seq 1 $MAX_RETRIES); do
    echo "健康检查尝试 $i/$MAX_RETRIES..."

    if command -v curl >/dev/null 2>&1; then
        if curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
            echo "后端健康检查通过"
            HEALTH_CHECK_SUCCESS=true
            break
        else
            echo "健康检查失败，等待${RETRY_DELAY}秒后重试..."
        fi
    elif command -v wget >/dev/null 2>&1; then
        if wget -q -O /dev/null http://localhost:8000/health; then
            echo "后端健康检查通过"
            HEALTH_CHECK_SUCCESS=true
            break
        else
            echo "健康检查失败，等待${RETRY_DELAY}秒后重试..."
        fi
    else
        echo "警告: 没有curl或wget，尝试检查后端进程状态..."
        if kill -0 $BACKEND_PID 2>/dev/null; then
            echo "后端进程存活，但无法进行HTTP健康检查"
            HEALTH_CHECK_SUCCESS=true
            break
        else
            echo "后端进程似乎已终止"
            # 继续重试，可能下次进程会启动
        fi
    fi

    if [ $i -lt $MAX_RETRIES ]; then
        sleep $RETRY_DELAY
    fi
done

if [ "$HEALTH_CHECK_SUCCESS" = false ]; then
    echo "错误: 后端健康检查失败，继续启动但后端可能不可用"
fi

# 检查后端是否启动成功
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo "错误：FastAPI后端启动失败"
    echo "检查日志..."
    exit 1
fi

echo "FastAPI后端启动成功，PID: $BACKEND_PID"

# 检查后端是否在监听端口
# 使用ss命令检查端口，如果ss不存在则尝试curl健康检查
if command -v ss >/dev/null 2>&1; then
    if ! ss -tln | grep -q ":8000 "; then
        echo "警告: FastAPI可能未在8000端口监听"
    else
        echo "FastAPI正在8000端口监听"
    fi
elif command -v curl >/dev/null 2>&1; then
    if ! curl -s -f http://localhost:8000/health >/dev/null 2>&1; then
        echo "警告: FastAPI健康检查失败"
    else
        echo "FastAPI健康检查通过"
    fi
else
    echo "警告: 无法检查FastAPI端口状态"
fi

# 启动nginx（前台运行）
echo "启动nginx..."
echo "检查前端静态文件..."
if [ -d "/app/frontend/dist" ]; then
    echo "前端dist目录存在，内容:"
    ls -la /app/frontend/dist/
    if [ -f "/app/frontend/dist/index.html" ]; then
        echo "index.html存在"
    else
        echo "警告: index.html不存在!"
    fi
else
    echo "错误: /app/frontend/dist目录不存在!"
    echo "尝试查找前端文件..."
    find /app -name "index.html" 2>/dev/null | head -5
fi

echo "检查nginx配置..."
# 确保nginx pid目录存在
mkdir -p /app/run
mkdir -p /run/nginx
chmod 755 /app/run 2>/dev/null || true
chmod 755 /run/nginx 2>/dev/null || true
nginx -t -c /app/nginx.conf

echo "启动nginx服务..."
exec nginx -c /app/nginx.conf -g "daemon off;"