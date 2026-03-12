"""
内心议会API端点

管理内心议会的启动、进度查询和结果获取
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.database import get_db
from ..models.schemas import CouncilStart, CouncilResponse, ErrorResponse
from ..services.council_service import CouncilService
from .dependencies import get_current_user_id, get_verified_session
from ..database.models import Council, Session
from ..utils.rate_limiter import check_auth_rate_limit

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/health")
async def council_health_check(db: AsyncSession = Depends(get_db)):
    """议会服务健康检查"""
    from ..services.external_apis import ExternalAPIService
    import logging

    logger = logging.getLogger(__name__)
    health_status = {
        "service": "council",
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {}
    }

    # 检查数据库连接
    try:
        await db.execute("SELECT 1")
        health_status["checks"]["database"] = {"status": "healthy", "detail": "连接正常"}
    except Exception as e:
        logger.error(f"数据库连接检查失败: {e}")
        health_status["checks"]["database"] = {"status": "unhealthy", "detail": str(e)}
        health_status["status"] = "unhealthy"

    # 检查 DashScope API 配置
    external_apis = ExternalAPIService()
    if external_apis.client is None:
        health_status["checks"]["dashscope_api"] = {"status": "warning", "detail": "API密钥未设置，将使用模拟响应"}
        # 不标记为不健康，因为模拟模式仍可工作
    else:
        health_status["checks"]["dashscope_api"] = {"status": "healthy", "detail": "API客户端已初始化"}

    return health_status


async def _get_owned_council(council_id: str, user_id: int, db: AsyncSession) -> Council:
    stmt = (
        select(Council)
        .join(Session, Council.session_id == Session.id)
        .where(Council.id == council_id, Session.user_id == user_id)
    )
    result = await db.execute(stmt)
    council = result.scalar_one_or_none()
    if not council:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="议会不存在或无权访问")
    return council


@router.post("/start", response_model=CouncilResponse, responses={400: {"model": ErrorResponse}})
async def start_council(
    council_data: CouncilStart,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    _rate_limit = Depends(check_auth_rate_limit),
):
    """启动内心议会"""
    try:
        council_service = CouncilService(db)
        await get_verified_session(council_data.session_id, user_id, db)

        # 启动议会
        council = await council_service.start_council(
            session_id=council_data.session_id,
            topic=council_data.topic,
            max_rounds=council_data.max_rounds,
            background_tasks=background_tasks
        )

        logger.info(f"内心议会启动: {council.council_id}")
        return council

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"启动议会失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="启动议会失败，请稍后重试"
        )


@router.get("/{council_id}")
async def get_council(
    council_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取议会详情"""
    try:
        await _get_owned_council(council_id, user_id, db)
        council_service = CouncilService(db)
        council = await council_service.get_council(council_id)

        if not council:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="议会不存在"
            )

        return council

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取议会失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取议会失败"
        )


@router.get("/session/{session_id}/active")
async def get_active_council(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """获取会话的活跃议会"""
    try:
        council_service = CouncilService(db)
        council = await council_service.get_active_council(session_id)

        if not council:
            return {"has_active": False}

        return {
            "has_active": True,
            "council": council
        }

    except Exception as e:
        logger.error(f"获取活跃议会失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取活跃议会失败"
        )


@router.post("/{council_id}/cancel")
async def cancel_council(
    council_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    _rate_limit = Depends(check_auth_rate_limit),
):
    """取消议会"""
    try:
        await _get_owned_council(council_id, user_id, db)
        logger.info(f"用户 {user_id} 取消议会 {council_id}")
        council_service = CouncilService(db)
        success = await council_service.cancel_council(council_id)

        if success:
            return {"message": "议会已取消"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="取消议会失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"取消议会失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="取消议会失败"
        )


@router.get("/{council_id}/progress")
async def get_council_progress(
    council_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取议会进度"""
    try:
        await _get_owned_council(council_id, user_id, db)
        council_service = CouncilService(db)
        progress = await council_service.get_progress(council_id)

        if not progress:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="议会不存在"
            )

        return progress

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取议会进度失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取议会进度失败"
        )


@router.get("/session/{session_id}/history")
async def get_council_history(
    session_id: str,
    limit: int = 10,
    offset: int = 0,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """获取议会历史"""
    try:
        council_service = CouncilService(db)
        history = await council_service.get_history(
            session_id=session_id,
            limit=limit,
            offset=offset
        )

        return {
            "session_id": session_id,
            "history": history,
            "total": len(history),
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"获取议会历史失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取议会历史失败"
        )


@router.post("/{council_id}/continue")
async def continue_council(
    council_id: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
    _rate_limit = Depends(check_auth_rate_limit),
):
    """继续执行已暂停的议会"""
    try:
        await _get_owned_council(council_id, user_id, db)
        logger.info(f"用户 {user_id} 继续议会 {council_id}")
        council_service = CouncilService(db)
        success = await council_service.continue_council(
            council_id=council_id,
            background_tasks=background_tasks
        )

        if success:
            return {"message": "议会已继续"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="继续议会失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"继续议会失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="继续议会失败"
        )
