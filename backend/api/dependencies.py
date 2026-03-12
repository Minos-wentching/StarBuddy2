"""
共享 API 依赖

提取公共的认证、权限校验等逻辑，避免代码重复。
"""

import logging
from fastapi import Request, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..auth.security import verify_token
from ..database.database import get_db
from ..database.models import Session

logger = logging.getLogger(__name__)


def _normalize_token(raw_token: str | None) -> str:
    """规范化令牌字符串，去除 Bearer 前缀与首尾空白。"""
    if not raw_token:
        return ""
    token = raw_token.strip()
    if token.startswith("Bearer "):
        token = token[7:].strip()
    return token


def _is_jwt_like(token: str) -> bool:
    """判断令牌是否符合 JWT 基本形态（3段）。"""
    return bool(token) and token.count(".") == 2


async def get_auth_token(request: Request) -> str:
    """从请求头获取认证令牌（X-Auth-Token 或 Authorization Bearer），也支持查询参数"""
    import urllib.parse

    is_sse_request = request.url.path.startswith("/api/sse/")
    query_token_raw = request.query_params.get("token")
    query_token = _normalize_token(urllib.parse.unquote(query_token_raw)) if query_token_raw else ""
    x_auth_token = _normalize_token(request.headers.get("X-Auth-Token"))
    authz_token = _normalize_token(request.headers.get("Authorization"))

    # SSE 场景下优先使用 query token；其他接口优先使用请求头 token。
    candidates = (
        [("query", query_token), ("x-auth-token", x_auth_token), ("authorization", authz_token)]
        if is_sse_request
        else [("x-auth-token", x_auth_token), ("authorization", authz_token), ("query", query_token)]
    )

    auth_header = ""
    for source, token in candidates:
        if not token:
            continue
        if _is_jwt_like(token):
            auth_header = token
            logger.debug(f"从{source}获取JWT令牌: {token[:50]}...")
            break
        logger.warning(f"忽略非JWT格式令牌来源 {source}: 长度={len(token)}")

    # 如果都不是JWT格式，回退到第一个非空令牌，让验证阶段给出统一401
    if not auth_header:
        for source, token in candidates:
            if token:
                auth_header = token
                logger.debug(f"回退使用{source}令牌: {token[:50]}...")
                break

    if not auth_header:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少认证令牌",
            headers={"WWW-Authenticate": "Custom"},
        )

    # 记录令牌前50个字符用于调试
    logger.debug(f"获取到令牌: {auth_header[:50]}... (长度: {len(auth_header)})")
    return auth_header


async def get_current_user_id(request: Request) -> int:
    """从请求头获取并验证令牌，返回用户ID"""
    token = await get_auth_token(request)
    try:
        payload = verify_token(token)
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )
        return user_id
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"令牌验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )


async def get_verified_session(
    session_id: str,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
) -> Session:
    """验证会话存在且属于当前用户，返回 Session 对象"""
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
