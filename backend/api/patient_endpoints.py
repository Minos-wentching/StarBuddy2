"""
用户端（孤独症患者端）档案与设置 API

说明：
- 数据存放在 users.settings JSON 中，避免引入新表/迁移成本。
- 监护人端与用户端默认使用同一账号，因此直接读写当前登录用户的数据。
"""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..api.dependencies import get_current_user_id
from ..database.database import get_db
from ..database.models import User
from ..models.schemas import (
    PatientProfile,
    PatientProfileUpdate,
    PatientSettings,
    PatientSettingsUpdate,
)

logger = logging.getLogger(__name__)

router = APIRouter()

DEFAULT_INSTRUCTIONS = [
    "找到水杯",
    "喝一口水",
    "找到椅子",
    "坐下来",
    "听一首歌",
    "休息",
    "画一幅画",
    "跳一跳",
]


def _normalize_instructions(raw) -> list[str]:
    if not isinstance(raw, list):
        return []
    cleaned: list[str] = []
    for item in raw:
        text = str(item or "").strip()
        if not text:
            continue
        cleaned.append(text)
    return cleaned


def _merge_patient_settings(settings: dict) -> PatientSettings:
    raw_settings = settings.get("patient_settings", {})
    raw_settings = raw_settings if isinstance(raw_settings, dict) else {}

    raw_instructions = _normalize_instructions(raw_settings.get("instructions"))
    instructions = raw_instructions if raw_instructions else list(DEFAULT_INSTRUCTIONS)

    raw_theme = raw_settings.get("theme", {})
    raw_theme = raw_theme if isinstance(raw_theme, dict) else {}
    theme = {
        "baseColor": str(raw_theme.get("baseColor") or "#0B1B3A"),
        "enableTransition": bool(raw_theme.get("enableTransition", False)),
        "transitionToColor": (
            str(raw_theme.get("transitionToColor")).strip()
            if raw_theme.get("transitionToColor") is not None and str(raw_theme.get("transitionToColor")).strip()
            else None
        ),
        "transitionDurationSec": int(raw_theme.get("transitionDurationSec", 30) or 30),
    }

    return PatientSettings(instructions=instructions, theme=theme)


@router.get("/patient-profile", response_model=PatientProfile)
async def get_patient_profile(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取用户端档案（目前仅 display_name）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    settings = dict(user.settings or {})
    profile = settings.get("patient_profile", {})
    profile = profile if isinstance(profile, dict) else {}

    display_name = str(profile.get("display_name") or "").strip()
    return PatientProfile(display_name=display_name)


@router.put("/patient-profile", response_model=PatientProfile)
async def update_patient_profile(
    payload: PatientProfileUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新用户端档案（display_name）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    next_settings = dict(user.settings or {})
    next_settings["patient_profile"] = {
        "display_name": payload.display_name.strip(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(settings=next_settings, updated_at=datetime.utcnow())
    )

    logger.info("patient_profile updated: user_id=%s", user_id)
    return PatientProfile(display_name=next_settings["patient_profile"]["display_name"])


@router.get("/patient-settings", response_model=PatientSettings)
async def get_patient_settings(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """获取用户端设置（指令列表/主题）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    settings = dict(user.settings or {})
    return _merge_patient_settings(settings)


@router.put("/patient-settings", response_model=PatientSettings)
async def update_patient_settings(
    payload: PatientSettingsUpdate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """更新用户端设置（指令列表/主题）"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    instructions = _normalize_instructions(payload.instructions)
    if not instructions:
        instructions = list(DEFAULT_INSTRUCTIONS)

    theme = payload.theme.model_dump()
    # Normalize empty strings to None
    if theme.get("transitionToColor") is not None and not str(theme.get("transitionToColor")).strip():
        theme["transitionToColor"] = None

    next_settings = dict(user.settings or {})
    next_settings["patient_settings"] = {
        "instructions": instructions,
        "theme": theme,
        "updated_at": datetime.utcnow().isoformat(),
    }

    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(settings=next_settings, updated_at=datetime.utcnow())
    )

    logger.info("patient_settings updated: user_id=%s", user_id)
    return _merge_patient_settings(next_settings)

