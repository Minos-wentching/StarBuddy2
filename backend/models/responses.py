"""
API响应模型

标准化的API响应格式
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class BaseResponse(BaseModel):
    """基础响应"""
    success: bool = True
    message: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DataResponse(BaseResponse, Generic[T]):
    """数据响应"""
    data: Optional[T] = None


class ListResponse(BaseResponse, Generic[T]):
    """列表响应"""
    data: List[T] = []
    total: int = 0
    page: int = 1
    page_size: int = 10
    total_pages: int = 0


class ErrorResponse(BaseResponse):
    """错误响应"""
    success: bool = False
    error_code: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None


class PaginationParams(BaseModel):
    """分页参数"""
    page: int = Field(1, ge=1, description="页码")
    page_size: int = Field(10, ge=1, le=100, description="每页数量")
    sort_by: Optional[str] = None
    sort_order: Optional[str] = Field("asc", regex="^(asc|desc)$")


class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    app: str
    version: str
    environment: str
    timestamp: str
    checks: Dict[str, Any] = {}


# 特定端点响应
class LoginResponse(DataResponse[Dict[str, str]]):
    """登录响应"""
    pass


class RegisterResponse(DataResponse[Dict[str, Any]]):
    """注册响应"""
    pass


class DialogueProcessResponse(DataResponse[Dict[str, Any]]):
    """对话处理响应"""
    pass


class CouncilStartResponse(DataResponse[Dict[str, Any]]):
    """议会启动响应"""
    pass


class SnapshotCreateResponse(DataResponse[Dict[str, Any]]):
    """快照创建响应"""
    pass


class VersionTreeResponse(DataResponse[Dict[str, Any]]):
    """版本树响应"""
    pass


# SSE事件响应
class SSEEventResponse(BaseModel):
    """SSE事件响应"""
    event: str
    data: Dict[str, Any]
    timestamp: str


# 状态响应
class PersonaStateResponse(DataResponse[Dict[str, Any]]):
    """人格状态响应"""
    pass


class SessionStateResponse(DataResponse[Dict[str, Any]]):
    """会话状态响应"""
    pass


class EmotionAnalysisResponse(DataResponse[Dict[str, Any]]):
    """情绪分析响应"""
    pass


# 管理响应
class SystemMetricsResponse(DataResponse[Dict[str, Any]]):
    """系统指标响应"""
    pass


class UserStatsResponse(DataResponse[Dict[str, Any]]):
    """用户统计响应"""
    pass


# 工具函数
def success_response(data: Any = None, message: str = "成功") -> Dict[str, Any]:
    """成功响应"""
    return {
        "success": True,
        "message": message,
        "data": data,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def error_response(message: str, error_code: str = None, details: Dict[str, Any] = None) -> Dict[str, Any]:
    """错误响应"""
    return {
        "success": False,
        "message": message,
        "error_code": error_code,
        "error_details": details,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def paginated_response(
    data: List[Any],
    total: int,
    page: int,
    page_size: int,
    message: str = "成功"
) -> Dict[str, Any]:
    """分页响应"""
    total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0

    return {
        "success": True,
        "message": message,
        "data": data,
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }