"""
简单的内存速率限制器

基于滑动窗口算法，限制特定key（如IP地址）的请求频率。
"""

import time
import logging
from collections import defaultdict
from typing import Optional
from fastapi import Request, HTTPException, status

logger = logging.getLogger(__name__)


class RateLimiter:
    """滑动窗口速率限制器"""

    def __init__(self, max_requests: int = 10, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _clean_old_requests(self, key: str):
        """清理过期的请求记录"""
        now = time.time()
        cutoff = now - self.window_seconds
        self._requests[key] = [
            t for t in self._requests[key] if t > cutoff
        ]

    def is_allowed(self, key: str) -> bool:
        """检查请求是否被允许"""
        self._clean_old_requests(key)
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(time.time())
        return True

    def remaining(self, key: str) -> int:
        """返回剩余可用请求数"""
        self._clean_old_requests(key)
        return max(0, self.max_requests - len(self._requests[key]))


# 认证端点速率限制器：每分钟最多10次请求
auth_rate_limiter = RateLimiter(max_requests=10, window_seconds=60)


def get_client_ip(request: Request) -> str:
    """获取客户端IP地址"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def check_auth_rate_limit(request: Request) -> None:
    """检查认证接口的速率限制，作为FastAPI依赖使用"""
    client_ip = get_client_ip(request)
    if not auth_rate_limiter.is_allowed(client_ip):
        logger.warning(f"认证接口速率限制触发: IP={client_ip}")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
            headers={"Retry-After": str(auth_rate_limiter.window_seconds)},
        )
