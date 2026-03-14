"""
Inner Mirror 主应用入口

FastAPI应用配置和路由注册
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api_config import config, get_config
from .utils.config_validator import log_config_summary
from .database.database import engine, Base
from .api import router as api_router

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时
    logger.info(f"启动 {config.APP_NAME} v{config.APP_VERSION}")

    # 记录配置摘要
    log_config_summary()

    # 初始化数据库（创建表）
    logger.info("检查并创建数据库表...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库表创建失败: {e}", exc_info=True)

    # 预加载 Embedding 模型
    logger.info("正在预加载 Embedding 模型 (可能需要一段时间)...")
    try:
        from .services.memory_service import preload_embedding_model
        from starlette.concurrency import run_in_threadpool
        await run_in_threadpool(preload_embedding_model)
        logger.info("Embedding 模型预加载完成")
    except Exception as e:
        logger.error(f"Embedding 模型加载失败: {e}")

    # 预初始化 MemoryStore 单例（ChromaDB client + collection）
    logger.info("正在预初始化 MemoryStore...")
    try:
        from .services.memory_service import MemoryStore
        from starlette.concurrency import run_in_threadpool
        await run_in_threadpool(MemoryStore)
        logger.info("MemoryStore 预初始化完成")
    except Exception as e:
        logger.error(f"MemoryStore 预初始化失败: {e}")

    yield

    # 关闭时
    logger.info("关闭应用...")


# 创建FastAPI应用
app = FastAPI(
    title=config.APP_NAME,
    version=config.APP_VERSION,
    description="Inner Mirror - 基于内部家庭系统（IFS）的心理疗愈系统",
    lifespan=lifespan,
    docs_url="/docs" if config.is_development else None,
    redoc_url="/redoc" if config.is_development else None,
)

# CORS配置
# 根据配置决定允许的来源
allowed_origins = config.allowed_origins_list
if not allowed_origins:
    if config.is_development:
        logger.warning("CORS: 没有配置ALLOWED_ORIGINS，开发环境允许所有来源（不推荐）")
        allowed_origins = ["*"]
    else:
        logger.warning("CORS: 生产环境没有配置ALLOWED_ORIGINS，将不允许任何来源")
        allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理器"""
    logger.error(f"未处理的异常: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "服务器内部错误",
            "error": str(exc) if config.is_development else "Internal server error",
        },
    )


# 健康检查端点
@app.get("/health", tags=["健康检查"])
async def health_check():
    """健康检查端点"""
    import time
    from datetime import datetime

    # 基础健康状态
    status = "healthy"

    # 检查数据库连接
    db_healthy = False
    try:
        async with engine.begin() as conn:
            await conn.execute("SELECT 1")
        db_healthy = True
    except Exception as e:
        logger.warning(f"数据库健康检查失败: {e}")
        status = "degraded"

    # 检查外部API连接（可选）
    # 这里可以添加对其他依赖服务的检查

    return {
        "status": status,
        "app": config.APP_NAME,
        "version": config.APP_VERSION,
        "environment": config.ENVIRONMENT,
        "timestamp": datetime.now().isoformat(),
        "checks": {
            "database": db_healthy,
            "api": True  # 假设API总是可用的
        },
        "details": {
            "database_url": config.DATABASE_URL if config.is_development else "hidden",
            "log_level": config.LOG_LEVEL,
            "uptime": "N/A"  # 可以添加应用启动时间跟踪
        }
    }


# 注册API路由
app.include_router(api_router, prefix="/api")

# 本地上传文件静态服务（开发/自部署使用）
try:
    from pathlib import Path

    uploads_dir = Path("data") / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=str(uploads_dir)), name="uploads")
except Exception as e:
    logger.warning(f"静态上传目录挂载失败: {e}")

# 根端点（主要用于健康检查）
@app.get("/")
async def root():
    """根端点"""
    return {
        "message": f"欢迎使用 {config.APP_NAME} API",
        "version": config.APP_VERSION,
        "docs": "/docs" if config.is_development else None,
        "health": "/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=config.is_development,
        log_level=config.LOG_LEVEL.lower(),
    )
