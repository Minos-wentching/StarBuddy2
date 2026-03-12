"""
版本存档API端点

管理心理状态版本快照，支持Git式回溯
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.database import get_db
from ..models.schemas import SnapshotCreate, SnapshotResponse, VersionTree, ErrorResponse
from ..services.version_service import VersionService
from .dependencies import get_current_user_id, get_verified_session
from ..database.models import Session

logger = logging.getLogger(__name__)

router = APIRouter()


async def _ensure_session_owner(session_id: str, user_id: int, db: AsyncSession) -> Session:
    stmt = select(Session).where(Session.id == session_id, Session.is_active == True)
    result = await db.execute(stmt)
    session = result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"会话不存在或已关闭: {session_id}")
    if session.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问此会话")
    return session


@router.post("/snapshot", response_model=SnapshotResponse, responses={400: {"model": ErrorResponse}})
async def create_snapshot(
    snapshot_data: SnapshotCreate,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """创建版本快照"""
    try:
        await _ensure_session_owner(snapshot_data.session_id, user_id, db)
        version_service = VersionService(db)

        snapshot = await version_service.create_snapshot(
            session_id=snapshot_data.session_id,
            state_data=snapshot_data.state_data,
            tags=snapshot_data.tags or []
        )

        logger.info(f"版本快照创建: {snapshot.id}")
        return snapshot

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建快照失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建快照失败，请稍后重试"
        )


@router.get("/snapshot/{snapshot_id}")
async def get_snapshot(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取快照详情"""
    try:
        version_service = VersionService(db)
        snapshot = await version_service.get_snapshot(snapshot_id)

        if not snapshot:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="快照不存在"
            )
        await _ensure_session_owner(snapshot.session_id, user_id, db)

        return snapshot

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取快照失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取快照失败"
        )


@router.get("/session/{session_id}/tree")
async def get_version_tree(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db),
):
    """获取版本树"""
    try:
        version_service = VersionService(db)
        tree = await version_service.get_version_tree(session_id)

        return tree

    except Exception as e:
        logger.error(f"获取版本树失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取版本树失败"
        )


@router.get("/session/{session_id}/snapshots")
async def list_snapshots(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    persona: str = None,
    min_intensity: float = None,
    max_intensity: float = None,
    tags: str = None,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db),
):
    """列出快照"""
    try:
        version_service = VersionService(db)

        # 解析标签
        tag_list = tags.split(",") if tags else []

        # 构建过滤条件
        filters = {}
        if persona:
            filters["persona"] = persona
        if min_intensity is not None:
            filters["min_intensity"] = min_intensity
        if max_intensity is not None:
            filters["max_intensity"] = max_intensity
        if tag_list:
            filters["tags"] = tag_list

        snapshots = await version_service.list_snapshots(
            session_id=session_id,
            limit=limit,
            offset=offset,
            filters=filters
        )

        return {
            "session_id": session_id,
            "snapshots": snapshots,
            "total": len(snapshots),
            "limit": limit,
            "offset": offset,
            "filters": filters
        }

    except Exception as e:
        logger.error(f"列出快照失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="列出快照失败"
        )


@router.post("/session/{session_id}/restore/{snapshot_id}")
async def restore_snapshot(
    session_id: str,
    snapshot_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """恢复到指定快照"""
    try:
        version_service = VersionService(db)

        success = await version_service.restore_snapshot(
            session_id=session_id,
            snapshot_id=snapshot_id
        )

        if success:
            return {"message": "快照恢复成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="恢复快照失败"
            )

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复快照失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复快照失败"
        )


@router.delete("/snapshot/{snapshot_id}")
async def delete_snapshot(
    snapshot_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """删除快照"""
    try:
        version_service = VersionService(db)

        snapshot = await version_service.get_snapshot(snapshot_id)
        if not snapshot:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="快照不存在")
        await _ensure_session_owner(snapshot.session_id, user_id, db)
        success = await version_service.delete_snapshot(snapshot_id)

        if success:
            return {"message": "快照删除成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="删除快照失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除快照失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除快照失败"
        )


@router.post("/session/{session_id}/branch")
async def create_branch(
    session_id: str,
    branch_name: str,
    from_snapshot: str = None,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """创建分支"""
    try:
        version_service = VersionService(db)

        branch = await version_service.create_branch(
            session_id=session_id,
            branch_name=branch_name,
            from_snapshot=from_snapshot
        )

        return {
            "message": "分支创建成功",
            "branch": branch
        }

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"创建分支失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建分支失败"
        )


@router.get("/session/{session_id}/branches")
async def list_branches(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """列出分支"""
    try:
        version_service = VersionService(db)
        branches = await version_service.list_branches(session_id)

        return {
            "session_id": session_id,
            "branches": branches
        }

    except Exception as e:
        logger.error(f"列出分支失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="列出分支失败"
        )
