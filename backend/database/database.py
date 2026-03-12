"""
数据库配置和连接管理
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

from ..api_config import config

logger = logging.getLogger(__name__)

# SQLite需要特殊处理URL
if config.DATABASE_URL.startswith("sqlite"):
    # SQLite异步需要特殊URL格式
    database_url = config.DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")
else:
    database_url = config.DATABASE_URL

# 创建异步引擎
engine = create_async_engine(
    database_url,
    echo=config.is_development,  # 开发环境输出SQL语句
    poolclass=NullPool if config.DATABASE_URL.startswith("sqlite") else None,
    pool_pre_ping=True,  # 连接前检查
    pool_recycle=3600,  # 连接回收时间（秒）
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# 声明基类
Base = declarative_base()


async def get_db():
    """
    获取数据库会话依赖项

    使用示例:
    @app.get("/items/")
    async def read_items(db: AsyncSession = Depends(get_db)):
        ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    """初始化数据库（创建表）"""
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("数据库初始化完成")
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def close_db():
    """关闭数据库连接"""
    try:
        await engine.dispose()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接时出错: {e}")
        raise


# 数据库健康检查
async def check_db_health() -> dict:
    """检查数据库连接健康状况"""
    try:
        async with AsyncSessionLocal() as session:
            # 执行简单查询
            result = await session.execute("SELECT 1")
            success = result.scalar() == 1

            return {
                "status": "healthy" if success else "unhealthy",
                "database": config.DATABASE_URL.split("://")[0],
                "connected": success,
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "database": config.DATABASE_URL.split("://")[0],
            "connected": False,
            "error": str(e),
        }


if __name__ == "__main__":
    import asyncio

    async def test_connection():
        """测试数据库连接"""
        print("测试数据库连接...")
        health = await check_db_health()
        print(f"数据库健康状态: {health}")

        if health["connected"]:
            print("数据库连接成功!")
        else:
            print(f"数据库连接失败: {health.get('error', '未知错误')}")

    asyncio.run(test_connection())