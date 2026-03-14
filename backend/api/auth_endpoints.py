"""
认证相关API端点

简化的基于用户名/ID的认证，无密码依赖
"""

import logging
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.database import get_db
from ..models.schemas import (
    UserCreate, UserLogin, UserResponse, Token,
    ErrorResponse, UserUpdate, RefreshTokenRequest, QuickLoginRequest,
    OnboardingParseRequest, OnboardingParseResponse,
    OnboardingArchiveListResponse, OnboardingArchiveItem,
    OnboardingRestoreRequest, OnboardingRestoreResponse
)
from ..auth.security import (
    create_access_token, create_refresh_token, verify_token, 
    refresh_access_token
)
from ..services.auth_service import AuthService
from ..services.external_apis import ExternalAPIService
from ..services.counselor_service import CounselorService
from ..database.models import Session
from sqlalchemy import update
from ..utils.rate_limiter import check_auth_rate_limit
from .dependencies import get_auth_token, get_current_user_id

logger = logging.getLogger(__name__)

router = APIRouter()

MAX_ONBOARDING_ARCHIVES = 20

MAX_MUSIC_UPLOAD_BYTES = 25 * 1024 * 1024  # 25MB


def _normalize_trauma_event(raw: dict, index: int = 0, default_source: str = "onboarding_fixed") -> dict:
    now_iso = datetime.utcnow().isoformat()
    title = str(raw.get("title") or raw.get("trigger_event") or raw.get("triggerEvent") or "未命名事件").strip()
    trigger_event = str(raw.get("trigger_event") or raw.get("triggerEvent") or title).strip()
    trauma_event = str(raw.get("trauma_event") or raw.get("traumaText") or raw.get("trauma_text") or trigger_event).strip()
    source_type = str(raw.get("source_type") or raw.get("sourceType") or default_source)
    event_id = str(raw.get("event_id") or raw.get("id") or f"event_{index + 1}")

    intensity_raw = raw.get("intensity", 0.58)
    try:
      intensity_num = float(intensity_raw)
    except Exception:
      intensity_num = 0.58
    if intensity_num > 1:
      intensity_num = max(0.0, min(1.0, intensity_num / 10.0))
    else:
      intensity_num = max(0.0, min(1.0, intensity_num))

    return {
        "event_id": event_id,
        "title": title,
        "trigger_event": trigger_event,
        "trauma_event": trauma_event,
        "intensity": intensity_num,
        "persona_hint": str(raw.get("persona_hint") or raw.get("personaHint") or ("firefighters" if intensity_num >= 0.72 else "exiles")),
        "source_type": source_type,
        "created_at": str(raw.get("created_at") or raw.get("createdAt") or now_iso),
        "updated_at": str(raw.get("updated_at") or raw.get("updatedAt") or now_iso),
        "event_rank": int(raw.get("event_rank") or raw.get("orb_rank") or raw.get("orbRank") or (index + 1)),
    }


def _events_to_legacy_orbs(events: list[dict]) -> list[dict]:
    rows = []
    for index, event in enumerate(events):
        row = {
            "id": event.get("event_id", f"orb_{index + 1}"),
            "title": event.get("title", "未命名记忆"),
            "trigger_event": event.get("trigger_event", ""),
            "trauma_text": event.get("trauma_event", ""),
            "intensity": event.get("intensity", 0.58),
            "persona_hint": event.get("persona_hint", "exiles"),
            "source_type": event.get("source_type", "onboarding_fixed"),
            "created_at": event.get("created_at", ""),
            "orb_rank": event.get("event_rank", index + 1),
        }
        rows.append(row)
    return rows


def _read_trauma_event_sets(onboarding: dict) -> tuple[list[dict], list[dict], bool]:
    fixed_new = onboarding.get("trauma_events_fixed", [])
    custom_new = onboarding.get("trauma_events_custom", [])
    initialized_new = bool(onboarding.get("trauma_events_initialized", False))

    if isinstance(fixed_new, list) and fixed_new:
        fixed_events = [_normalize_trauma_event(item if isinstance(item, dict) else {}, idx, "onboarding_fixed") for idx, item in enumerate(fixed_new)]
    else:
        legacy_fixed = onboarding.get("memory_orbs_fixed", [])
        legacy_fixed = legacy_fixed if isinstance(legacy_fixed, list) else []
        fixed_events = [_normalize_trauma_event(item if isinstance(item, dict) else {}, idx, "onboarding_fixed") for idx, item in enumerate(legacy_fixed)]

    if isinstance(custom_new, list) and custom_new:
        custom_events = [_normalize_trauma_event(item if isinstance(item, dict) else {}, idx, "custom") for idx, item in enumerate(custom_new)]
    else:
        legacy_custom = onboarding.get("memory_orbs_custom", [])
        legacy_custom = legacy_custom if isinstance(legacy_custom, list) else []
        custom_events = [_normalize_trauma_event(item if isinstance(item, dict) else {}, idx, "custom") for idx, item in enumerate(legacy_custom)]

    initialized = initialized_new or bool(onboarding.get("memory_orbs_initialized", False))
    return fixed_events, custom_events, initialized


def _build_onboarding_archive_item(onboarding: dict) -> dict:
    profile_version = int(onboarding.get("profile_version", 1) or 1)
    created_at = onboarding.get("updated_at") or onboarding.get("created_at")
    fixed_events, custom_events, initialized = _read_trauma_event_sets(onboarding)
    return {
        "profile_version": profile_version,
        "created_at": str(created_at or ""),
        "profile_digest": str(onboarding.get("profile_digest", "") or ""),
        "trauma_hypothesis": str(onboarding.get("trauma_hypothesis", "") or ""),
        "user_core_info": onboarding.get("user_core_info", []) if isinstance(onboarding.get("user_core_info", []), list) else [],
        "core_beliefs": onboarding.get("core_beliefs", []) if isinstance(onboarding.get("core_beliefs", []), list) else [],
        "persona_portraits": onboarding.get("persona_portraits", {}) if isinstance(onboarding.get("persona_portraits", {}), dict) else {},
        "profile_confirmed": bool(onboarding.get("profile_confirmed", False)),
        "exiles_system_prompt": str(onboarding.get("exiles_system_prompt", "") or ""),
        "firefighters_system_prompt": str(onboarding.get("firefighters_system_prompt", "") or ""),
        "trauma_events_fixed": fixed_events,
        "trauma_events_custom": custom_events,
        "trauma_events_initialized": initialized,
        "memory_orbs_fixed": _events_to_legacy_orbs(fixed_events),
        "memory_orbs_custom": _events_to_legacy_orbs(custom_events),
        "memory_orbs_initialized": initialized,
    }


def _sanitize_archive_item(item: dict) -> dict:
    fixed_events, custom_events, initialized = _read_trauma_event_sets(item)
    return {
        "profile_version": int(item.get("profile_version", 1) or 1),
        "created_at": str(item.get("created_at", "") or ""),
        "profile_digest": str(item.get("profile_digest", "") or ""),
        "trauma_hypothesis": str(item.get("trauma_hypothesis", "") or ""),
        "user_core_info": item.get("user_core_info", []) if isinstance(item.get("user_core_info", []), list) else [],
        "core_beliefs": item.get("core_beliefs", []) if isinstance(item.get("core_beliefs", []), list) else [],
        "persona_portraits": item.get("persona_portraits", {}) if isinstance(item.get("persona_portraits", {}), dict) else {},
        "profile_confirmed": bool(item.get("profile_confirmed", False)),
        "exiles_system_prompt": str(item.get("exiles_system_prompt", "") or ""),
        "firefighters_system_prompt": str(item.get("firefighters_system_prompt", "") or ""),
        "trauma_events_fixed": fixed_events,
        "trauma_events_custom": custom_events,
        "trauma_events_initialized": initialized,
        "memory_orbs_fixed": _events_to_legacy_orbs(fixed_events),
        "memory_orbs_custom": _events_to_legacy_orbs(custom_events),
        "memory_orbs_initialized": initialized,
    }


def _build_onboarding_from_archive_item(archive_item: dict, existing_onboarding: dict) -> dict:
    fixed_events, custom_events, initialized = _read_trauma_event_sets(existing_onboarding)
    keep_fields = {
        "trauma_events_fixed": archive_item.get("trauma_events_fixed", fixed_events),
        "trauma_events_custom": archive_item.get("trauma_events_custom", custom_events),
        "trauma_events_initialized": bool(archive_item.get("trauma_events_initialized", initialized)),
        "memory_orbs_fixed": archive_item.get("memory_orbs_fixed", _events_to_legacy_orbs(archive_item.get("trauma_events_fixed", fixed_events))),
        "memory_orbs_custom": archive_item.get("memory_orbs_custom", _events_to_legacy_orbs(archive_item.get("trauma_events_custom", custom_events))),
        "memory_orbs_initialized": bool(archive_item.get("memory_orbs_initialized", archive_item.get("trauma_events_initialized", initialized))),
    }
    now_iso = datetime.utcnow().isoformat()
    return {
        "exiles_system_prompt": archive_item.get("exiles_system_prompt", ""),
        "firefighters_system_prompt": archive_item.get("firefighters_system_prompt", ""),
        "trauma_hypothesis": archive_item.get("trauma_hypothesis", ""),
        "user_core_info": archive_item.get("user_core_info", []),
        "core_beliefs": archive_item.get("core_beliefs", []),
        "profile_digest": archive_item.get("profile_digest", ""),
        "persona_portraits": archive_item.get("persona_portraits", {}),
        "profile_version": int(archive_item.get("profile_version", 1) or 1),
        "profile_confirmed": bool(archive_item.get("profile_confirmed", False)),
        "created_at": archive_item.get("created_at") or now_iso,
        "updated_at": now_iso,
        **keep_fields,
    }


@router.post("/register", response_model=UserResponse, responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
async def register(
    user_data: UserCreate,
    _rate_limit: None = Depends(check_auth_rate_limit),
    db: AsyncSession = Depends(get_db)
):
    """用户注册（仅使用用户名）"""
    try:
        auth_service = AuthService(db)

        # 创建用户
        user = await auth_service.create_user(username=user_data.username)

        logger.info(f"用户注册成功: {user.username}")
        return user

    except HTTPException:
        raise
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"用户注册失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"注册失败: {str(e)}"
        )


@router.post("/login", response_model=Token, responses={401: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
async def login(
    data: UserLogin,
    _rate_limit: None = Depends(check_auth_rate_limit),
    db: AsyncSession = Depends(get_db)
):
    """用户登录（仅使用用户名）"""
    try:
        auth_service = AuthService(db)

        # 通过用户名查找用户
        user = await auth_service.get_user_by_username(data.username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在，请先注册"
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已被停用"
            )

        # 创建令牌
        access_token = create_access_token(
            data={"user_id": user.id, "username": user.username}
        )
        refresh_token = create_refresh_token(
            data={"user_id": user.id, "username": user.username}
        )

        # 更新最后登录时间
        await auth_service.update_last_login(user.id)

        logger.info(f"用户登录成功: {user.username}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "custom",
            "expires_in": 14400  # 4小时
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"用户登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="登录失败，请稍后重试"
        )


@router.post("/quick-login", response_model=Token, responses={400: {"model": ErrorResponse}, 429: {"model": ErrorResponse}})
async def quick_login(
    data: QuickLoginRequest,
    _rate_limit: None = Depends(check_auth_rate_limit),
    db: AsyncSession = Depends(get_db)
):
    """快速登录（仅用户名，不存在则自动注册）"""
    try:
        auth_service = AuthService(db)
        username = data.username.strip()
        
        # 1. 检查用户是否存在
        user = await auth_service.get_user_by_username(username)
        
        if not user:
            # 2. 如果不存在，自动注册
            try:
                user = await auth_service.create_user(username=username)
            except ValueError as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户账户已被停用"
            )

        # 3. 创建令牌
        access_token = create_access_token(
            data={"user_id": user.id, "username": user.username}
        )
        refresh_token = create_refresh_token(
            data={"user_id": user.id, "username": user.username}
        )

        # 更新最后登录时间
        await auth_service.update_last_login(user.id)

        logger.info(f"快速登录成功: {user.username}")
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "custom",
            "expires_in": 14400  # 4小时
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"快速登录失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"登录失败: {str(e)}"
        )


@router.post("/refresh", response_model=Token, responses={401: {"model": ErrorResponse}})
async def refresh_token_endpoint(
    data: RefreshTokenRequest
):
    """刷新访问令牌"""
    try:
        new_access_token = refresh_access_token(data.refresh_token)
        if not new_access_token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的刷新令牌"
            )

        return {
            "access_token": new_access_token,
            "token_type": "custom",
            "expires_in": 14400
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"刷新令牌失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="令牌刷新失败"
        )


@router.get("/me", response_model=UserResponse, responses={401: {"model": ErrorResponse}})
async def get_current_user(
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户信息"""
    try:
        # 验证令牌
        payload = verify_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )

        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="用户不存在"
            )

        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取用户信息失败"
        )


@router.put("/me", response_model=UserResponse, responses={401: {"model": ErrorResponse}})
async def update_current_user(
    user_data: UserUpdate,
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db)
):
    """更新当前用户信息"""
    try:
        # 验证令牌
        payload = verify_token(token)
        user_id = payload.get("user_id")

        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的令牌"
            )

        auth_service = AuthService(db)
        user = await auth_service.update_user(user_id, user_data.dict(exclude_unset=True))

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="用户不存在"
            )

        logger.info(f"用户信息更新成功: {user.username}")
        return user

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新用户信息失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户信息失败"
        )


@router.post("/logout")
async def logout(
    token: str = Depends(get_auth_token)
):
    """用户登出（客户端应删除令牌）"""
    # 注意：JWT是无状态的，服务器端无法直接使令牌失效
    # 实际实现可能需要令牌黑名单或使用短有效期
    return {"message": "登出成功，请客户端删除令牌"}


@router.post("/onboarding/parse", response_model=OnboardingParseResponse, responses={401: {"model": ErrorResponse}})
async def parse_onboarding(
    payload: OnboardingParseRequest,
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db)
):
    """解析首次登录四道简答题并写入用户画像与会话提示词"""
    try:
        parsed_token = verify_token(token)
        user_id = parsed_token.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        external_api = ExternalAPIService()
        counselor = CounselorService(external_api)
        answers_dict = payload.answers.dict()
        parsed = await counselor.parse_onboarding_answers(answers_dict)

        settings = dict(user.settings or {})
        existing_onboarding = settings.get("ifs_onboarding", {}) if isinstance(settings.get("ifs_onboarding", {}), dict) else {}
        existing_fixed_events, existing_custom_events, existing_initialized = _read_trauma_event_sets(existing_onboarding)
        previous_version = int(existing_onboarding.get("profile_version", 0) or 0)
        next_version = previous_version + 1 if previous_version > 0 else 1
        settings["ifs_onboarding_completed"] = True
        existing_archives = settings.get("ifs_onboarding_archives", [])
        archives = existing_archives if isinstance(existing_archives, list) else []

        settings["ifs_onboarding"] = {
            "exiles_system_prompt": parsed.get("exiles_system_prompt", ""),
            "firefighters_system_prompt": parsed.get("firefighters_system_prompt", ""),
            "trauma_hypothesis": parsed.get("trauma_hypothesis", ""),
            "user_core_info": parsed.get("user_core_info", []),
            "core_beliefs": parsed.get("core_beliefs", []),
            "profile_digest": parsed.get("profile_digest", ""),
            "persona_portraits": parsed.get("persona_portraits", {}),
            "profile_version": next_version,
            "profile_confirmed": False,
            "trauma_events_fixed": existing_fixed_events,
            "trauma_events_custom": existing_custom_events,
            "trauma_events_initialized": existing_initialized,
            "memory_orbs_fixed": _events_to_legacy_orbs(existing_fixed_events),
            "memory_orbs_custom": _events_to_legacy_orbs(existing_custom_events),
            "memory_orbs_initialized": existing_initialized,
            "created_at": existing_onboarding.get("created_at") or datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }

        archives.append(_build_onboarding_archive_item(settings["ifs_onboarding"]))
        archives = sorted(
            [_sanitize_archive_item(item) for item in archives if isinstance(item, dict)],
            key=lambda item: int(item.get("profile_version", 1) or 1),
            reverse=True,
        )[:MAX_ONBOARDING_ARCHIVES]
        settings["ifs_onboarding_archives"] = archives
        await auth_service.update_user(user_id, {"settings": settings})

        if payload.session_id:
            session_result = await db.execute(
                select(Session).where(Session.id == payload.session_id, Session.user_id == user_id)
            )
            session = session_result.scalar_one_or_none()
            if session:
                persona_state = dict(session.persona_state or {})
                persona_state.update({
                    "onboarding_completed": True,
                    "exiles_system_prompt": parsed.get("exiles_system_prompt", ""),
                    "firefighters_system_prompt": parsed.get("firefighters_system_prompt", ""),
                    "onboarding_profile": {
                        "profile_digest": parsed.get("profile_digest", ""),
                        "trauma_hypothesis": parsed.get("trauma_hypothesis", ""),
                        "user_core_info": parsed.get("user_core_info", []),
                        "core_beliefs": parsed.get("core_beliefs", []),
                        "profile_version": next_version,
                        "profile_confirmed": False,
                    },
                    "persona_portraits": parsed.get("persona_portraits", {}),
                    "event_context": {
                        "active_event_id": "",
                        "active_trigger_event": parsed.get("trauma_hypothesis", ""),
                        "active_trauma_event": "",
                        "active_event_source": "onboarding_init",
                        "event_history": [],
                    },
                })
                await db.execute(
                    update(Session)
                    .where(Session.id == payload.session_id)
                    .values(persona_state=persona_state)
                )
                await db.commit()

        return OnboardingParseResponse(
            completed=True,
            exiles_system_prompt=parsed.get("exiles_system_prompt", ""),
            firefighters_system_prompt=parsed.get("firefighters_system_prompt", ""),
            trauma_hypothesis=parsed.get("trauma_hypothesis", ""),
            user_core_info=parsed.get("user_core_info", []),
            core_beliefs=parsed.get("core_beliefs", []),
            profile_digest=parsed.get("profile_digest", ""),
            persona_portraits=parsed.get("persona_portraits", {}),
            profile_version=next_version,
            profile_confirmed=False,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"解析首次问卷失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="解析问卷失败，请稍后重试"
        )


@router.post("/onboarding/music-upload", responses={401: {"model": ErrorResponse}})
async def upload_onboarding_music(
    file: UploadFile = File(...),
    user_id: int = Depends(get_current_user_id),
):
    """
    上传监护人提供的本地音乐文件（可选）。

    返回：{ url, filename }
    - 文件会保存到 ./data/uploads/music/<user_id>/ 下
    - 通过后端静态路由 /uploads/ 访问（见 backend/main.py）
    """
    import os
    import uuid
    from pathlib import Path

    if not file:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="未选择文件")

    content_type = str(file.content_type or "").lower()
    if not content_type.startswith("audio/"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="仅支持音频文件上传")

    raw_name = os.path.basename(str(file.filename or "music"))
    safe_name = raw_name.replace("..", "").replace("/", "_").replace("\\", "_").strip() or "music"
    suffix = Path(safe_name).suffix[:12]
    unique_name = f"{uuid.uuid4().hex}{suffix}"

    base_dir = Path("data") / "uploads" / "music" / str(user_id)
    base_dir.mkdir(parents=True, exist_ok=True)
    dest = base_dir / unique_name

    size = 0
    try:
        with dest.open("wb") as f:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                size += len(chunk)
                if size > MAX_MUSIC_UPLOAD_BYTES:
                    raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="文件过大")
                f.write(chunk)
    finally:
        try:
            await file.close()
        except Exception:
            pass

    url = f"/uploads/music/{user_id}/{unique_name}"
    return {"url": url, "filename": safe_name}


@router.get("/onboarding/archives", response_model=OnboardingArchiveListResponse, responses={401: {"model": ErrorResponse}})
async def get_onboarding_archives(
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db)
):
    """获取人格画像存档历史"""
    try:
        parsed_token = verify_token(token)
        user_id = parsed_token.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        settings = dict(user.settings or {})
        onboarding = settings.get("ifs_onboarding", {}) if isinstance(settings.get("ifs_onboarding", {}), dict) else {}
        archives = settings.get("ifs_onboarding_archives", [])
        archive_rows = [_sanitize_archive_item(item) for item in archives if isinstance(item, dict)]

        if onboarding:
            current_version = int(onboarding.get("profile_version", 1) or 1)
            if not any(int(item.get("profile_version", 0) or 0) == current_version for item in archive_rows):
                archive_rows.append(_build_onboarding_archive_item(onboarding))
        else:
            current_version = 1

        archive_rows = sorted(
            archive_rows,
            key=lambda item: int(item.get("profile_version", 1) or 1),
            reverse=True,
        )[:MAX_ONBOARDING_ARCHIVES]

        return OnboardingArchiveListResponse(
            current_version=current_version,
            total=len(archive_rows),
            archives=[OnboardingArchiveItem(**{
                "profile_version": item.get("profile_version", 1),
                "created_at": item.get("created_at", ""),
                "profile_digest": item.get("profile_digest", ""),
                "trauma_hypothesis": item.get("trauma_hypothesis", ""),
                "user_core_info": item.get("user_core_info", []),
                "core_beliefs": item.get("core_beliefs", []),
                "persona_portraits": item.get("persona_portraits", {}),
                "profile_confirmed": item.get("profile_confirmed", False),
            }) for item in archive_rows],
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取人格画像存档失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取人格画像存档失败"
        )


@router.post("/onboarding/restore", response_model=OnboardingRestoreResponse, responses={401: {"model": ErrorResponse}})
async def restore_onboarding_archive(
    payload: OnboardingRestoreRequest,
    token: str = Depends(get_auth_token),
    db: AsyncSession = Depends(get_db)
):
    """恢复人格画像到指定版本"""
    try:
        parsed_token = verify_token(token)
        user_id = parsed_token.get("user_id")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌")

        auth_service = AuthService(db)
        user = await auth_service.get_user_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

        settings = dict(user.settings or {})
        onboarding = settings.get("ifs_onboarding", {}) if isinstance(settings.get("ifs_onboarding", {}), dict) else {}
        archives = settings.get("ifs_onboarding_archives", [])
        archive_rows = [_sanitize_archive_item(item) for item in archives if isinstance(item, dict)]

        target = next(
            (item for item in archive_rows if int(item.get("profile_version", 0) or 0) == int(payload.profile_version)),
            None,
        )
        if not target:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="指定画像版本不存在")

        restored_onboarding = _build_onboarding_from_archive_item(target, onboarding)
        settings["ifs_onboarding_completed"] = True
        settings["ifs_onboarding"] = restored_onboarding
        settings["ifs_onboarding_archives"] = archive_rows
        await auth_service.update_user(user_id, {"settings": settings})

        if payload.session_id:
            session_result = await db.execute(
                select(Session).where(Session.id == payload.session_id, Session.user_id == user_id)
            )
            session = session_result.scalar_one_or_none()
            if session:
                persona_state = dict(session.persona_state or {})
                persona_state.update({
                    "onboarding_completed": True,
                    "exiles_system_prompt": restored_onboarding.get("exiles_system_prompt", ""),
                    "firefighters_system_prompt": restored_onboarding.get("firefighters_system_prompt", ""),
                    "onboarding_profile": {
                        "profile_digest": restored_onboarding.get("profile_digest", ""),
                        "trauma_hypothesis": restored_onboarding.get("trauma_hypothesis", ""),
                        "user_core_info": restored_onboarding.get("user_core_info", []),
                        "core_beliefs": restored_onboarding.get("core_beliefs", []),
                        "profile_version": restored_onboarding.get("profile_version", 1),
                        "profile_confirmed": restored_onboarding.get("profile_confirmed", False),
                    },
                    "persona_portraits": restored_onboarding.get("persona_portraits", {}),
                    "event_context": {
                        "active_event_id": "",
                        "active_trigger_event": restored_onboarding.get("trauma_hypothesis", ""),
                        "active_trauma_event": "",
                        "active_event_source": "onboarding_restore",
                        "event_history": [],
                    },
                })
                await db.execute(
                    update(Session)
                    .where(Session.id == payload.session_id)
                    .values(persona_state=persona_state)
                )
                await db.commit()

        return OnboardingRestoreResponse(
            restored=True,
            profile_version=int(restored_onboarding.get("profile_version", 1) or 1),
            profile_confirmed=bool(restored_onboarding.get("profile_confirmed", False)),
            profile_digest=str(restored_onboarding.get("profile_digest", "") or ""),
            persona_portraits=restored_onboarding.get("persona_portraits", {}),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"恢复人格画像版本失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="恢复人格画像版本失败"
        )
