"""
认证和安全工具

JWT令牌生成验证等
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from fastapi import HTTPException, status

from ..api_config import config

logger = logging.getLogger(__name__)

# JWT配置
SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES

# 记录SECRET_KEY信息用于调试
logger.debug(f"JWT配置加载: ALGORITHM={ALGORITHM}, ACCESS_TOKEN_EXPIRE_MINUTES={ACCESS_TOKEN_EXPIRE_MINUTES}")
logger.debug(f"SECRET_KEY长度: {len(SECRET_KEY) if SECRET_KEY else 0}")
if SECRET_KEY:
    logger.debug(f"SECRET_KEY前缀: {SECRET_KEY[:20]}...")


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "access"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.debug(f"创建访问令牌: expires={expire}, data={data}")
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any]) -> str:
    """创建刷新令牌（有效期更长）"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 7天有效期

    to_encode.update({"exp": expire, "iat": datetime.utcnow(), "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    logger.debug(f"创建刷新令牌: expires={expire}, data={data}")
    return encoded_jwt


def verify_token(token: str, token_type: str = "access") -> Dict[str, Any]:
    """验证令牌并返回载荷"""
    try:
        # 记录令牌长度和前50个字符用于调试
        logger.debug(f"验证令牌: {token[:50]}... (长度: {len(token)}, 类型: {token_type})")

        # 检查令牌基本格式
        if not token or token.count('.') != 2:
            logger.warning(f"令牌格式不正确: 点号数量={token.count('.')}")
            raise JWTError(f"令牌格式不正确: Not enough segments")

        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

        # 检查令牌类型
        if payload.get("type") != token_type:
            logger.warning(f"令牌类型不匹配: expected={token_type}, got={payload.get('type')}")
            raise JWTError("令牌类型不匹配")

        # 检查过期时间
        expire = payload.get("exp")
        if expire is None:
            logger.warning("令牌缺少过期时间")
            raise JWTError("令牌缺少过期时间")

        if datetime.utcnow() > datetime.fromtimestamp(expire):
            logger.warning("令牌已过期")
            raise JWTError("令牌已过期")

        logger.debug(f"令牌验证成功: user_id={payload.get('user_id')}")
        return payload

    except JWTError as e:
        logger.warning(f"令牌验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌",
            headers={"WWW-Authenticate": "Custom"},
        )


def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """解码令牌（不验证过期）"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM], options={"verify_exp": False})
        return payload
    except JWTError as e:
        logger.warning(f"令牌解码失败: {e}")
        return None


def refresh_access_token(refresh_token: str) -> Optional[str]:
    """使用刷新令牌获取新的访问令牌"""
    try:
        payload = verify_token(refresh_token, token_type="refresh")

        # 从刷新令牌中提取用户信息
        user_id = payload.get("user_id")
        username = payload.get("username")

        if not user_id or not username:
            logger.warning("刷新令牌缺少用户信息")
            return None

        # 创建新的访问令牌
        access_token = create_access_token({"user_id": user_id, "username": username})
        return access_token

    except (JWTError, HTTPException) as e:
        logger.warning(f"刷新令牌失败: {e}")
        return None


if __name__ == "__main__":
    # 测试JWT令牌
    test_data = {"user_id": 1, "username": "testuser"}
    token = create_access_token(test_data)
    print(f"访问令牌: {token}")

    try:
        payload = verify_token(token)
        print(f"令牌载荷: {payload}")
    except Exception as e:
        print(f"令牌验证失败: {e}")