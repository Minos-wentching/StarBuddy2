"""
SSE (Server-Sent Events) 端点

实时推送人格切换、情绪更新、议会状态等事件
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import AsyncGenerator
from fastapi import APIRouter, Request, HTTPException, status, Depends
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.schemas import (
    SSEEvent, PersonaSwitchEvent, EmotionUpdateEvent, CouncilUpdateEvent
)
from ..database.database import get_db
from ..api.dependencies import get_current_user_id
from ..database.models import Session

logger = logging.getLogger(__name__)

router = APIRouter()

# SSE连接管理器（简化版）
class ConnectionManager:
    def __init__(self):
        # session_id -> [queue1, queue2, ...]
        self.active_connections = {}

    async def connect(self, session_id: str):
        """建立SSE连接"""
        queue = asyncio.Queue()
        self.active_connections.setdefault(session_id, []).append(queue)
        logger.info(f"SSE连接建立: {session_id}")
        return queue

    async def disconnect(self, session_id: str, queue: asyncio.Queue = None):
        """断开SSE连接"""
        if session_id in self.active_connections:
            if queue is None:
                del self.active_connections[session_id]
            else:
                queues = self.active_connections[session_id]
                if queue in queues:
                    queues.remove(queue)
                if not queues:
                    del self.active_connections[session_id]
            logger.info(f"SSE连接断开: {session_id}")

    async def send_event(self, session_id: str, event: dict):
        """向特定会话发送事件"""
        if session_id in self.active_connections:
            for queue in list(self.active_connections[session_id]):
                await queue.put(event)


connection_manager = ConnectionManager()


async def event_generator(session_id: str, request: Request) -> AsyncGenerator:
    """SSE事件生成器"""
    queue = await connection_manager.connect(session_id)

    try:
        # 发送连接确认事件
        yield {
            "event": "connected",
            "data": json.dumps({
                "session_id": session_id,
                "message": "SSE连接已建立"
            })
        }

        # 保持连接，发送心跳
        while True:
            if await request.is_disconnected():
                logger.info(f"客户端断开连接: {session_id}")
                break

            try:
                # 等待事件或超时
                event = await asyncio.wait_for(queue.get(), timeout=30.0)

                # 发送事件
                yield {
                    "event": event.get("event_type", "message"),
                    "data": json.dumps(event.get("data", {}))
                }

            except asyncio.TimeoutError:
                # 发送心跳保持连接
                yield {
                    "event": "heartbeat",
                    "data": json.dumps({
                        "timestamp": datetime.now(timezone.utc).isoformat()
                    })
                }

    except asyncio.CancelledError:
        # 客户端取消连接
        logger.info(f"SSE连接被取消: {session_id}")
    finally:
        await connection_manager.disconnect(session_id, queue)


@router.get("/{session_id}")
async def sse_stream(
    session_id: str,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """SSE事件流端点"""
    # 验证会话ID（简化版，实际应验证会话存在和用户权限）
    if not session_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="会话ID不能为空"
        )

    # 验证会话存在且属于当前用户
    session_stmt = select(Session).where(
        Session.id == session_id, Session.is_active == True
    )
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话不存在或已关闭: {session_id}"
        )
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话"
        )

    # 返回SSE响应
    return EventSourceResponse(
        event_generator(session_id, request),
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        }
    )


async def _ensure_sse_session_owner(session_id: str, user_id: int, db: AsyncSession) -> Session:
    session_stmt = select(Session).where(
        Session.id == session_id, Session.is_active == True
    )
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"会话不存在或已关闭: {session_id}"
        )
    if session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="无权访问此会话"
        )
    return session


@router.post("/{session_id}/persona-switch")
async def trigger_persona_switch(
    session_id: str,
    event: PersonaSwitchEvent,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """触发人格切换事件（测试用）"""
    try:
        await _ensure_sse_session_owner(session_id, user_id, db)
        await connection_manager.send_event(session_id, {
            "event_type": "persona_switch",
            "data": event.dict()
        })
        return {"message": "人格切换事件已发送"}
    except Exception as e:
        logger.error(f"发送人格切换事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送事件失败"
        )


@router.post("/{session_id}/emotion-update")
async def trigger_emotion_update(
    session_id: str,
    event: EmotionUpdateEvent,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """触发情绪更新事件（测试用）"""
    try:
        await _ensure_sse_session_owner(session_id, user_id, db)
        await connection_manager.send_event(session_id, {
            "event_type": "emotion_update",
            "data": event.dict()
        })
        return {"message": "情绪更新事件已发送"}
    except Exception as e:
        logger.error(f"发送情绪更新事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送事件失败"
        )


@router.post("/{session_id}/council-update")
async def trigger_council_update(
    session_id: str,
    event: CouncilUpdateEvent,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """触发议会更新事件（测试用）"""
    try:
        await _ensure_sse_session_owner(session_id, user_id, db)
        await connection_manager.send_event(session_id, {
            "event_type": "council_update",
            "data": event.dict()
        })
        return {"message": "议会更新事件已发送"}
    except Exception as e:
        logger.error(f"发送议会更新事件失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="发送事件失败"
        )


@router.get("/{session_id}/status")
async def get_sse_status(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取SSE连接状态"""
    await _ensure_sse_session_owner(session_id, user_id, db)
    session_connections = connection_manager.active_connections.get(session_id, [])
    is_connected = len(session_connections) > 0
    total_connections = sum(
        len(queues) for queues in connection_manager.active_connections.values()
    )
    return {
        "session_id": session_id,
        "connected": is_connected,
        "active_connections": total_connections
    }


# 后台任务：定期清理无效连接
async def cleanup_inactive_connections():
    """清理无效的SSE连接，通过尝试放入心跳事件来检测死连接"""
    stale_connections = []
    for session_id, queues in connection_manager.active_connections.items():
        for queue in queues:
            try:
                # 尝试非阻塞放入心跳，如果队列满则认为连接可能已死
                queue.put_nowait({
                    "event_type": "heartbeat",
                    "data": {"timestamp": datetime.now(timezone.utc).isoformat()}
                })
            except asyncio.QueueFull:
                stale_connections.append((session_id, queue))
    for session_id, queue in stale_connections:
        await connection_manager.disconnect(session_id, queue)
        logger.info(f"清理无效SSE连接: {session_id}")
