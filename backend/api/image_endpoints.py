"""
疗愈相册 & 日记 API 端点
完善 handle_feedback 流程，移植自 Multiego orchestrator.handle_feedback
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database.database import get_db
from ..database.models import HealingImage, Session
from .dependencies import get_current_user_id
from ..models.schemas import DiaryFeedbackRequest, DiaryResponse
from ..services.external_apis import ExternalAPIService
from ..services.counselor_service import CounselorService
from ..services.manager_service import ManagerService
from ..services.council_service import CouncilService
from ..services.memory_service import MemoryStore
from ..services.dialogue_service import DialogueService
from ..api.sse_endpoints import connection_manager
from ..api_config import config

logger = logging.getLogger(__name__)

router = APIRouter()


def _compute_feedback_intensity(counselor_report, session: Session) -> float:
    """Multiego 对齐：core belief 强度 + 次人格衰减"""
    if counselor_report and counselor_report.core_beliefs:
        max_intensity = max(b.intensity for b in counselor_report.core_beliefs)
        raw = min(max_intensity / 10.0, 1.0)
    else:
        raw = float(session.emotion_intensity or 0.0)

    persona_state = session.persona_state or {}
    current_persona = session.current_persona or "manager"
    persona_switch_turn = int(persona_state.get("persona_switch_turn", 0))
    turn_count = int(persona_state.get("turn_count", 0))

    if current_persona != "manager" and persona_switch_turn > 0:
        turns_since_switch = max(0, turn_count - persona_switch_turn)
        decay_multiplier = max(0.0, 1.0 - turns_since_switch * config.INTENSITY_DECAY_RATE)
        return max(0.0, min(1.0, raw * decay_multiplier))

    return max(0.0, min(1.0, raw))


async def _ensure_session_owner(session_id: str, user_id: int, db: AsyncSession) -> Session:
    session_stmt = select(Session).where(Session.id == session_id, Session.is_active == True)
    session_result = await db.execute(session_stmt)
    session = session_result.scalar_one_or_none()
    if not session:
        raise HTTPException(status_code=404, detail=f"会话不存在或已关闭: {session_id}")
    if session.user_id != user_id:
        raise HTTPException(status_code=403, detail="无权访问此会话")
    return session


async def _get_owned_diary(diary_id: str, user_id: int, db: AsyncSession) -> HealingImage:
    stmt = select(HealingImage).where(HealingImage.id == diary_id)
    result = await db.execute(stmt)
    diary = result.scalar_one_or_none()
    if not diary:
        raise HTTPException(status_code=404, detail="日记不存在")
    await _ensure_session_owner(diary.session_id, user_id, db)
    return diary


@router.get("/{session_id}")
async def get_images(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取会话的疗愈图片列表"""
    await _ensure_session_owner(session_id, user_id, db)
    stmt = (
        select(HealingImage)
        .where(HealingImage.session_id == session_id)
        .order_by(HealingImage.created_at.desc())
    )
    result = await db.execute(stmt)
    images = result.scalars().all()
    return {
        "images": [
            {
                "id": img.id,
                "image_url": img.image_url,
                "diary_text": img.diary_text,
                "persona": img.persona,
                "feedback": img.feedback if hasattr(img, 'feedback') else None,
                "created_at": img.created_at,
            }
            for img in images
        ]
    }


@router.get("/diary/{diary_id}")
async def get_diary(
    diary_id: str,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """获取单条日记详情"""
    diary = await _get_owned_diary(diary_id, user_id, db)
    return {
        "id": diary.id,
        "session_id": diary.session_id,
        "image_url": diary.image_url,
        "diary_text": diary.diary_text,
        "persona": diary.persona,
        "feedback": diary.feedback if hasattr(diary, 'feedback') else None,
        "created_at": diary.created_at,
    }


@router.post("/diary/feedback")
async def add_diary_feedback(
    request: DiaryFeedbackRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user_id: int = Depends(get_current_user_id),
):
    """
    添加日记反馈（完整流程，移植自 Multiego orchestrator.handle_feedback）

    流程：
    1. 追加反馈到日记
    2. Counselor 重新分析反馈
    3. 将分析报告存入向量库
    4. 更新 intensity
    5. 根据阈值决定是否触发人格切换/议会
    """
    # 1. 获取日记
    diary = await _get_owned_diary(request.diary_id, user_id, db)

    # 2. 追加反馈（Multiego 风格：多次提交用换行分隔）
    existing_feedback = diary.feedback or ""
    if existing_feedback:
        new_feedback = existing_feedback + "\n" + request.feedback
    else:
        new_feedback = request.feedback

    # 更新数据库中的反馈
    await db.execute(
        update(HealingImage)
        .where(HealingImage.id == request.diary_id)
        .values(feedback=new_feedback)
    )
    await db.commit()

    # 3. 初始化服务
    external_api = ExternalAPIService()
    counselor = CounselorService(external_api)
    manager = ManagerService(external_api)

    # 4. Counselor 分析反馈 (移植自 Multiego handle_feedback)
    counselor_report = await counselor.analyze_trauma(request.feedback, diary.diary_text or "")

    # 5. 将反馈分析报告存入向量库
    if counselor_report:
        try:
            memory_store = MemoryStore()
            memory_store.store_report(counselor_report.dict(), request.feedback, user_id=user_id)
        except Exception as e:
            logger.warning(f"Failed to store feedback report to memory: {e}")

    # 7. 获取会话状态
    session = await _ensure_session_owner(diary.session_id, user_id, db)
    intensity = _compute_feedback_intensity(counselor_report, session)

    current_persona = session.current_persona if session else "manager"
    was_manager = current_persona == "manager"

    response_data = {
        "success": True,
        "diary_id": request.diary_id,
        "feedback": new_feedback,
        "intensity": intensity,
        "counselor_report": {
            "core_beliefs": [
                {"content": b.content, "valence": b.valence, "intensity": b.intensity}
                for b in counselor_report.core_beliefs
            ] if counselor_report else [],
            "trigger_event": counselor_report.trigger_event if counselor_report else "",
            "emotional_summary": counselor_report.emotional_summary if counselor_report else "",
        },
        "active_agent": current_persona,
        "message": "你落笔写下了心事，一切似乎更清晰了......"
    }

    # 8. 根据阈值决定是否触发人格切换 (移植自 Multiego handle_feedback)
    if was_manager and intensity > config.INTENSITY_SWITCH_THRESHOLD:
        # 触发次人格切换
        logger.info(f"High intensity ({intensity:.2f}) in feedback. Triggering personality switch.")

        # 调用 Manager.decide() 生成 events 和 character_profile
        manager_decision = await manager.decide(counselor_report)
        response_data["decision"] = {
            "target_agent": manager_decision.target_agent.value,
            "events": manager_decision.events,
            "character_profile": manager_decision.character_profile,
        }

        # 启动议会
        council_topic = manager_decision.council_topic or request.feedback[:100]
        council_service = CouncilService(db)
        council = await council_service.start_council(
            session_id=diary.session_id,
            topic=council_topic,
            max_rounds=config.COUNCIL_NEGOTIATION_ROUNDS,
            background_tasks=background_tasks
        )
        response_data["council_id"] = council.council_id
        response_data["council_active"] = True

        # 更新会话人格
        target_persona = manager_decision.target_agent.value
        persona_state = session.persona_state or {}
        turn_count = int(persona_state.get("turn_count", 0))
        persona_state["persona_switch_turn"] = turn_count

        await db.execute(
            update(Session)
            .where(Session.id == diary.session_id)
            .values(
                current_persona=target_persona,
                emotion_intensity=intensity,
                persona_state=persona_state,
            )
        )
        await db.commit()
        response_data["active_agent"] = target_persona

        # 生成新日记（Multiego handle_feedback 对齐）
        dialogue_service = DialogueService(db)
        await dialogue_service._generate_diary_entry(
            session_id=diary.session_id,
            persona=target_persona,
            user_input=request.feedback,
            report=counselor_report,
            manager_decision=manager_decision,
            user_id=user_id,
            persona_state=session.persona_state or {},
        )

        # SSE 推送
        background_tasks.add_task(
            connection_manager.send_event, diary.session_id, {
                "event_type": "feedback_triggered_switch",
                "data": {
                    "intensity": intensity,
                    "target_agent": target_persona,
                    "events": manager_decision.events,
                    "character_profile": manager_decision.character_profile,
                }
            }
        )

    elif not was_manager and intensity <= config.INTENSITY_RETURN_THRESHOLD:
        # 切回主人格
        persona_state = session.persona_state or {}
        persona_state["persona_switch_turn"] = 0
        await db.execute(
            update(Session)
            .where(Session.id == diary.session_id)
            .values(
                current_persona="manager",
                emotion_intensity=intensity,
                persona_state=persona_state,
            )
        )
        await db.commit()
        response_data["active_agent"] = "manager"
        response_data["switched_back"] = True
        response_data["message"] = "情绪平复中，已切回主人格。"

    response_data["can_edit_diary"] = response_data["active_agent"] == "manager"

    return response_data
