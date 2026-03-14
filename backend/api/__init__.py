"""
API路由注册
"""

from fastapi import APIRouter
from . import auth_endpoints, sse_endpoints, dialogue_endpoints, council_endpoints, version_endpoints, image_endpoints, social_endpoints, patient_endpoints

# 创建主路由器
router = APIRouter()

# 注册各个模块的路由器
router.include_router(auth_endpoints.router, prefix="/auth", tags=["认证"])
router.include_router(sse_endpoints.router, prefix="/sse", tags=["SSE"])
router.include_router(dialogue_endpoints.router, prefix="/dialogue", tags=["对话"])
router.include_router(council_endpoints.router, prefix="/council", tags=["内心议会"])
router.include_router(version_endpoints.router, prefix="/version", tags=["版本存档"])
router.include_router(image_endpoints.router, prefix="/images", tags=["疗愈相册"])
router.include_router(social_endpoints.router, prefix="/social", tags=["社交互动"])
router.include_router(patient_endpoints.router, prefix="/me", tags=["用户端设置"])
