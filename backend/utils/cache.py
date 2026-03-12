"""
简单内存缓存系统

提供带过期时间的键值缓存，支持异步操作。
主要用于缓存API响应、计算结果等，减少外部API调用和重复计算。
"""

import asyncio
import time
from typing import Any, Optional, Dict
from collections import OrderedDict

logger = None  # 可后续配置日志


class SimpleCache:
    """简单内存缓存，支持过期时间和最大容量"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化缓存
        :param max_size: 最大缓存条目数
        :param default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, Dict[str, Any]] = OrderedDict()
        self._lock = asyncio.Lock()

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值，如果过期或不存在则返回None"""
        async with self._lock:
            if key not in self._cache:
                return None

            entry = self._cache[key]
            if time.time() > entry["expires_at"]:
                # 过期，删除并返回None
                del self._cache[key]
                return None

            # 更新访问顺序（LRU）
            self._cache.move_to_end(key)
            return entry["value"]

    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        async with self._lock:
            # 如果达到最大容量，删除最旧的条目
            if len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]

            expires_at = time.time() + (ttl if ttl is not None else self.default_ttl)
            self._cache[key] = {
                "value": value,
                "expires_at": expires_at,
                "created_at": time.time()
            }
            # 确保键在末尾（最近使用）
            self._cache.move_to_end(key)

    async def delete(self, key: str) -> bool:
        """删除缓存键，返回是否成功"""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> None:
        """清空所有缓存"""
        async with self._lock:
            self._cache.clear()

    async def cleanup(self) -> int:
        """清理过期条目，返回清理的数量"""
        async with self._lock:
            now = time.time()
            expired_keys = [k for k, v in self._cache.items() if v["expires_at"] < now]
            for key in expired_keys:
                del self._cache[key]
            return len(expired_keys)

    async def size(self) -> int:
        """返回当前缓存条目数"""
        async with self._lock:
            return len(self._cache)

    async def keys(self) -> list[str]:
        """返回所有缓存键"""
        async with self._lock:
            return list(self._cache.keys())


# 全局缓存实例
# 用于缓存议会结果、API响应等
council_cache = SimpleCache(max_size=100, default_ttl=600)  # 议会缓存，10分钟
api_response_cache = SimpleCache(max_size=200, default_ttl=300)  # API响应缓存，5分钟


async def get_or_set(key: str, coroutine_func, ttl: Optional[int] = None, cache_instance: SimpleCache = None):
    """
    缓存获取模式：如果缓存存在则返回，否则执行协程函数并缓存结果
    :param key: 缓存键
    :param coroutine_func: 返回值的协程函数
    :param ttl: 可选的自定义TTL
    :param cache_instance: 使用的缓存实例，默认为api_response_cache
    :return: 缓存值或新计算的值
    """
    if cache_instance is None:
        cache_instance = api_response_cache

    cached = await cache_instance.get(key)
    if cached is not None:
        return cached

    value = await coroutine_func()
    await cache_instance.set(key, value, ttl)
    return value


def cache_key_council_progress(session_id: str, council_id: Optional[str] = None) -> str:
    """生成议会进度缓存键"""
    if council_id:
        return f"council:progress:{session_id}:{council_id}"
    return f"council:progress:{session_id}"


def cache_key_council_history(session_id: str, limit: int, offset: int) -> str:
    """生成议会历史缓存键"""
    return f"council:history:{session_id}:{limit}:{offset}"


def cache_key_api_response(endpoint: str, params: Dict[str, Any]) -> str:
    """生成API响应缓存键"""
    import hashlib
    param_str = str(sorted(params.items()))
    hash_digest = hashlib.md5(param_str.encode()).hexdigest()[:8]
    return f"api:{endpoint}:{hash_digest}"