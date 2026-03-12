"""
对话处理API端点

处理用户消息，触发情绪分析、人格切换和对话生成
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database.database import get_db
from ..models.schemas import DialogueMessage, DialogueResponse, ErrorResponse, SessionResponse, SessionCreate
from ..services.dialogue_service import DialogueService
from ..services.auth_service import AuthService
from ..services.external_apis import ExternalAPIService
from ..services.memory_service import MemoryStore
from ..database.models import Session, User, DialogueHistory, Council, HealingImage
from .dependencies import get_current_user_id, get_verified_session

logger = logging.getLogger(__name__)

router = APIRouter()


def _safe_float(raw_value, default=0.0) -> float:
    try:
        return float(raw_value)
    except (TypeError, ValueError):
        return float(default)


def _normalize_orb_intensity(raw_value, default=0.58) -> float:
    num = _safe_float(raw_value, default)
    if num > 1:
        num = num / 10.0
    return max(0.0, min(1.0, num))


def _parse_memory_document(document: str) -> dict:
    fields = {
        "belief": "",
        "valence": "",
        "intensity": "",
        "origin": "",
        "trigger": "",
        "user_said": "",
    }
    for raw_line in (document or "").splitlines():
        line = raw_line.strip()
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key_lower = key.strip().lower()
        value = value.strip()
        if key_lower == "core belief":
            fields["belief"] = value
        elif key_lower == "valence":
            fields["valence"] = value
        elif key_lower == "intensity":
            fields["intensity"] = value
        elif key_lower == "origin":
            fields["origin"] = value
        elif key_lower == "trigger":
            fields["trigger"] = value
        elif key_lower == "user said":
            fields["user_said"] = value
    return fields


@router.get("/sessions", responses={401: {"model": ErrorResponse}})
async def list_user_sessions(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取当前用户会话列表（按最近活跃时间倒序）"""
    try:
        auth_service = AuthService(db)
        sessions = await auth_service.get_user_sessions(user_id)
        return {
            "sessions": [
                {
                    "id": s.id,
                    "current_persona": s.current_persona,
                    "emotion_intensity": s.emotion_intensity,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                    "last_activity": s.last_activity.isoformat() if s.last_activity else None,
                    "is_active": s.is_active,
                }
                for s in sessions
            ]
        }
    except Exception as e:
        logger.error(f"获取用户会话列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话列表失败"
        )


@router.post("/session", response_model=SessionResponse, responses={401: {"model": ErrorResponse}})
async def create_session(
    session_data: SessionCreate,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """创建新对话会话"""
    try:
        auth_service = AuthService(db)
        # 构造初始数据
        init_data = {
            "current_persona": "manager",
            "emotion_intensity": 0.0,
            "persona_state": {}
        }
        session = await auth_service.create_session(user_id, init_data)
        if not session:
            raise HTTPException(status_code=500, detail="创建会话失败")
        
        return session
    except Exception as e:
        logger.error(f"创建会话异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/process", response_model=DialogueResponse, responses={400: {"model": ErrorResponse}, 401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def process_dialogue(
    message: DialogueMessage,
    background_tasks: BackgroundTasks,
    request: Request,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """处理用户对话消息"""
    try:
        session_id = message.session_id

        # 验证会话存在
        session_stmt = select(Session).where(Session.id == session_id, Session.is_active == True)
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"会话不存在或已关闭: {session_id}"
            )

        # 验证用户权限：会话必须属于当前用户
        if session.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问此会话"
            )

        # 创建对话服务
        dialogue_service = DialogueService(db)

        # 处理消息
        response = await dialogue_service.process_message(
            session_id=session_id,
            message=message.message,
            background_tasks=background_tasks,
            user_id=str(user_id)
        )

        logger.info(f"对话处理完成: session={session_id}, persona={response.persona}")
        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"对话处理失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="对话处理失败，请稍后重试"
        )


@router.get("/history/{session_id}", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def get_dialogue_history(
    session_id: str,
    limit: int = 50,
    offset: int = 0,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """获取对话历史"""
    try:
        dialogue_service = DialogueService(db)

        history = await dialogue_service.get_history(
            session_id=session_id,
            limit=limit,
            offset=offset
        )

        return {
            "session_id": session_id,
            "history": history,
            "total": len(history),
            "limit": limit,
            "offset": offset
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取对话历史失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取对话历史失败"
        )


@router.delete("/history/{session_id}", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def clear_dialogue_history(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """清空对话历史"""
    try:
        dialogue_service = DialogueService(db)

        success = await dialogue_service.clear_history(session_id)

        if success:
            return {"message": "对话历史已清空"}
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="清空对话历史失败"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清空对话历史失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="清空对话历史失败"
        )


@router.get("/session/{session_id}/status", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def get_session_status(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """获取会话状态"""
    try:
        # 查询消息计数
        from sqlalchemy import func
        count_stmt = select(func.count(DialogueHistory.id)).where(DialogueHistory.session_id == session_id)
        count_result = await db.execute(count_stmt)
        message_count = count_result.scalar() or 0

        # 返回会话状态
        return {
            "session_id": session_id,
            "current_persona": session.current_persona,
            "emotion_intensity": session.emotion_intensity,
            "persona_state": session.persona_state,
            "emotion_history": session.emotion_history,
            "message_count": message_count,
            "created_at": session.created_at.isoformat() if session.created_at else None,
            "last_activity": session.last_activity.isoformat() if session.last_activity else None,
            "is_active": session.is_active
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取会话状态失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取会话状态失败"
        )


@router.post("/session/{session_id}/reset", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def reset_session(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """重置会话状态"""
    try:
        from datetime import datetime
        from sqlalchemy import update

        # 重置会话状态到初始值
        reset_data = {
            "current_persona": "manager",
            "emotion_intensity": 0.0,
            "emotion_history": [],
            "persona_state": {},
            "last_activity": datetime.utcnow()
        }

        # 更新数据库
        update_stmt = (
            update(Session)
            .where(Session.id == session_id)
            .values(**reset_data)
        )
        await db.execute(update_stmt)
        await db.commit()

        # 可选：清除对话历史（根据需求决定是否保留历史）
        # delete_stmt = delete(DialogueHistory).where(DialogueHistory.session_id == session_id)
        # await db.execute(delete_stmt)
        # await db.commit()

        logger.info(f"会话已重置: {session_id}, 用户: {session.user_id}")

        return {
            "message": "会话状态已重置",
            "session_id": session_id,
            "reset_at": datetime.utcnow().isoformat(),
            "reset_fields": list(reset_data.keys())
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"重置会话失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="重置会话失败"
        )


@router.get("/memory-orbs/{session_id}", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def get_memory_orbs(
    session_id: str,
    session: Session = Depends(get_verified_session),
):
    """获取展示模式记忆球数据（优先 Chroma 记忆，回退到 session persona_state）"""
    try:
        memory_store = MemoryStore()
        entries = memory_store.get_all_beliefs(user_id=session.user_id)

        orbs = []
        seen = set()

        for entry in entries:
            metadata = entry.get("metadata") or {}
            parsed = _parse_memory_document(entry.get("document", ""))
            title = parsed["belief"] or parsed["trigger"] or "核心记忆"
            trigger_event = parsed["trigger"] or parsed["origin"] or title
            trauma_text = parsed["user_said"] or parsed["trigger"] or parsed["belief"] or title
            intensity = _normalize_orb_intensity(parsed["intensity"], 0.58)

            dedupe_key = (title, trigger_event)
            if dedupe_key in seen:
                continue
            seen.add(dedupe_key)

            if intensity >= 0.72:
                persona_hint = "firefighters"
            elif intensity >= 0.56:
                persona_hint = "exiles"
            else:
                persona_hint = "manager"

            orbs.append({
                "id": entry.get("id", ""),
                "title": title,
                "trauma_text": trauma_text,
                "trigger_event": trigger_event,
                "intensity": intensity,
                "persona_hint": persona_hint,
                "source_type": metadata.get("type", "core_belief"),
                "created_at": metadata.get("timestamp", ""),
            })

        orbs = sorted(
            orbs,
            key=lambda x: (x.get("intensity", 0.0), x.get("created_at", "")),
            reverse=True,
        )[:8]

        for index, orb in enumerate(orbs):
            orb["orb_rank"] = index + 1

        if not orbs:
            persona_state = session.persona_state or {}
            core_beliefs = persona_state.get("core_beliefs", []) if isinstance(persona_state, dict) else []
            for index, belief in enumerate(core_beliefs[:8]):
                intensity = _normalize_orb_intensity(belief.get("intensity", 6), 0.58)
                orbs.append({
                    "id": f"session_belief_{index}",
                    "title": str(belief.get("content", "") or "核心记忆"),
                    "trauma_text": str(
                        belief.get("origin_event", "")
                        or belief.get("content", "")
                        or "一次仍在影响你的情绪触发。"
                    ),
                    "trigger_event": str(
                        belief.get("origin_event", "")
                        or belief.get("content", "")
                        or "当前情绪冲突"
                    ),
                    "intensity": intensity,
                    "persona_hint": "firefighters" if intensity >= 0.72 else "exiles",
                    "source_type": "session_fallback",
                    "created_at": session.last_activity.isoformat() if session.last_activity else "",
                    "orb_rank": index + 1,
                })

        return {
            "session_id": session_id,
            "orbs": orbs,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取记忆球失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="获取记忆球失败"
        )


@router.get("/report/{session_id}", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def get_session_report(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """生成探索报告：聚合核心信念、人格画像、议会回顾、情绪趋势、咨询师寄语"""
    try:
        from sqlalchemy import func

        # 1. Core beliefs from persona_state
        persona_state = session.persona_state or {}
        core_beliefs = persona_state.get("core_beliefs", [])

        # 2. Persona portraits
        persona_portraits = persona_state.get("persona_portraits", {})

        # 3. Council summary - get latest completed council
        council_stmt = (
            select(Council)
            .where(Council.session_id == session_id, Council.status == "completed")
            .order_by(Council.completed_at.desc())
            .limit(1)
        )
        council_result = await db.execute(council_stmt)
        latest_council = council_result.scalar_one_or_none()
        council_summary = latest_council.conclusion if latest_council else ""

        # 4. Emotion trend from history
        emotion_trend = [e.get("intensity", 0) for e in (session.emotion_history or []) if isinstance(e, dict)]

        # 5. Self-presence from persona_state
        self_presence = persona_state.get("self_presence_clarity", None)
        self_presence_trend_val = persona_state.get("self_presence_trend", "stable")
        trend_map = {"improving": "持续提升中", "declining": "有所波动", "stable": "保持稳定"}
        self_presence_trend = trend_map.get(self_presence_trend_val, "保持稳定")

        # 6. Counselor note
        counselor_note = persona_state.get("self_presence_analysis", "")

        return {
            "session_id": session_id,
            "core_beliefs": core_beliefs,
            "persona_portraits": persona_portraits,
            "council_summary": council_summary,
            "emotion_trend": emotion_trend,
            "self_presence": self_presence,
            "self_presence_trend": self_presence_trend,
            "counselor_note": counselor_note,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成报告失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成报告失败"
        )


@router.get("/narrative/{session_id}", responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}})
async def get_session_narrative(
    session_id: str,
    session: Session = Depends(get_verified_session),
    db: AsyncSession = Depends(get_db)
):
    """将对话历史改写为第三人称叙事文本"""
    try:
        # Fetch dialogue history
        history_stmt = (
            select(DialogueHistory)
            .where(DialogueHistory.session_id == session_id)
            .order_by(DialogueHistory.created_at.asc())
            .limit(50)
        )
        history_result = await db.execute(history_stmt)
        history_rows = history_result.scalars().all()

        if not history_rows:
            return {"session_id": session_id, "chapters": [], "message": "暂无对话记录"}

        # Build conversation text
        conversation_text = ""
        for row in history_rows:
            conversation_text += f"用户: {row.message}\n"
            conversation_text += f"{row.persona}: {row.response}\n\n"

        # Fetch healing images for this session
        img_stmt = (
            select(HealingImage)
            .where(HealingImage.session_id == session_id)
            .order_by(HealingImage.created_at.asc())
        )
        img_result = await db.execute(img_stmt)
        images = img_result.scalars().all()
        image_urls = [img.image_url for img in images if img.image_url]

        # Use LLM to rewrite as narrative
        api_service = ExternalAPIService()
        narrative_prompt = (
            "你是一位文学化的心理叙事作家。请将以下心理咨询对话改写为一段第三人称的心理探索故事。"
            "要求：\n"
            "1. 分为 2-4 个章节，每章有标题\n"
            "2. 用温暖、富有诗意的语言\n"
            "3. 保留关键的情感转折和洞察\n"
            "4. 输出 JSON 格式：[{\"title\": \"章节标题\", \"content\": \"章节内容\"}]\n"
            "5. 只输出 JSON，不要其他内容\n\n"
            f"对话记录：\n{conversation_text}"
        )

        if api_service.client:
            from ..api_config import config
            model = config.DASHSCOPE_DIALOGUE_MODEL or "qwen-max"
            completion = await api_service.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": narrative_prompt}],
                temperature=0.8,
            )
            raw = completion.choices[0].message.content.strip()
            # Parse JSON from response
            import json, re
            json_match = re.search(r'\[.*\]', raw, re.DOTALL)
            if json_match:
                chapters = json.loads(json_match.group())
            else:
                chapters = [{"title": "你的故事", "content": raw}]
        else:
            # Mock response
            chapters = [
                {"title": "序章：一个声音的浮现", "content": "在一个安静的夜晚，ta 第一次听到了内心深处的声音……"},
                {"title": "对话：当脆弱被看见", "content": "那个一直被藏起来的小孩，终于有机会说出自己的感受……"},
            ]

        # Attach images to chapters
        for i, ch in enumerate(chapters):
            if i < len(image_urls):
                ch["image_url"] = image_urls[i]

        return {
            "session_id": session_id,
            "chapters": chapters,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"生成叙事文本失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="生成叙事文本失败"
        )
