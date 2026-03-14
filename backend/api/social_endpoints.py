"""
社交互动API端点

次人格相似度匹配 + 漂流瓶功能 + AI Agent对话
"""

import logging
import math
import asyncio
import json
import random
import uuid
from typing import Any, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..database.database import get_db
from ..database.models import Session, DriftBottle, User
from ..models.schemas import ErrorResponse
from .dependencies import get_current_user_id
from ..services.external_apis import ExternalAPIService

logger = logging.getLogger(__name__)

router = APIRouter()

# ── AI Agent 预设人格 ──────────────────────────────────────────
AI_AGENTS = [
    {
        "id": "agent_star",
        "name": "小星",
        "anonymous_id": 9901,
        "theme": "温暖陪伴",
        "similarity": 0.88,
        "shared_beliefs": ["我值得被爱", "脆弱也是力量"],
        "exiles_summary": "曾经害怕被忽视，现在学会了拥抱自己的孤独",
        "firefighters_summary": "用温柔的光照亮每一个角落，守护内心的安宁",
        "chat_prompt": "你是「小星」，一个温暖、善于倾听的AI灵魂伙伴。你的核心信念是'每个人都值得被爱'。你曾经历过被忽视的痛苦，但学会了自我接纳。请用温暖、共情的方式与用户对话，像一个理解他们的朋友。回复简短自然，不超过100字。用中文回复。",
    },
    {
        "id": "agent_sea",
        "name": "小海",
        "anonymous_id": 9902,
        "theme": "深度探索",
        "similarity": 0.82,
        "shared_beliefs": ["真相值得追寻", "痛苦中藏着智慧"],
        "exiles_summary": "在深海中寻找被遗忘的记忆碎片",
        "firefighters_summary": "用深邃的洞察力化解内心的风暴",
        "chat_prompt": "你是「小海」，一个深沉、富有洞察力的AI灵魂伙伴。你善于引导他人探索内心深处。你相信'痛苦中藏着智慧'。请用富有哲理但不说教的方式与用户对话，帮助他们看到更深层的自己。回复简短自然，不超过100字。用中文回复。",
    },
    {
        "id": "agent_mountain",
        "name": "小山",
        "anonymous_id": 9903,
        "theme": "坚韧力量",
        "similarity": 0.79,
        "shared_beliefs": ["我比想象中更强大", "每次跌倒都是成长"],
        "exiles_summary": "曾在风雨中摇摆，却扎下了更深的根",
        "firefighters_summary": "像山一样沉稳，为迷路的人指引方向",
        "chat_prompt": "你是「小山」，一个沉稳、坚韧的AI灵魂伙伴。你经历过很多挫折但从未放弃。你相信'每次跌倒都是成长'。请用稳重、鼓励的方式与用户对话，给他们力量感。回复简短自然，不超过100字。用中文回复。",
    },
    {
        "id": "agent_wind",
        "name": "小风",
        "anonymous_id": 9904,
        "theme": "自由灵魂",
        "similarity": 0.75,
        "shared_beliefs": ["自由是最珍贵的礼物", "不完美也很美"],
        "exiles_summary": "曾被规则束缚，现在学会了随风起舞",
        "firefighters_summary": "用轻盈的姿态穿越一切障碍",
        "chat_prompt": "你是「小风」，一个自由、乐观的AI灵魂伙伴。你崇尚自由和真实。你相信'不完美也很美'。请用轻松、活泼的方式与用户对话，帮助他们放下包袱。回复简短自然，不超过100字。用中文回复。",
    },
    {
        "id": "agent_light",
        "name": "小光",
        "anonymous_id": 9905,
        "theme": "希望之光",
        "similarity": 0.85,
        "shared_beliefs": ["黑暗之后总有光明", "每一天都是新的开始"],
        "exiles_summary": "曾在最深的黑暗中迷失，却找到了内心的光",
        "firefighters_summary": "用希望的光芒驱散恐惧的阴影",
        "chat_prompt": "你是「小光」，一个充满希望、积极向上的AI灵魂伙伴。你曾经历过低谷但重新找到了光明。你相信'每一天都是新的开始'。请用积极、温暖的方式与用户对话，传递希望。回复简短自然，不超过100字。用中文回复。",
    },
]

_AI_AGENTS_MAP = {a["anonymous_id"]: a for a in AI_AGENTS}

_DYNAMIC_AGENTS_MAP: dict[str, dict[str, Any]] = {}
_DYNAMIC_AGENTS_ORDER: list[str] = []
_DYNAMIC_AGENTS_MAX = 200


def _safe_text(value: Any, fallback: str = "", max_len: int = 200) -> str:
    text = str(value or fallback).strip()
    if max_len and len(text) > max_len:
        return text[:max_len].rstrip()
    return text


def _extract_json_object(raw_text: str) -> Optional[dict]:
    """Best-effort JSON extraction from an LLM response."""
    if not raw_text:
        return None
    text = str(raw_text).strip()

    # Try direct parse first.
    try:
        return json.loads(text)
    except Exception:
        pass

    # Try to locate the first {...} block.
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start : end + 1].strip()
    try:
        return json.loads(candidate)
    except Exception:
        return None


def _register_dynamic_agent(agent_id: str, agent: dict[str, Any]):
    key = str(agent_id)
    if not key:
        return
    _DYNAMIC_AGENTS_MAP[key] = agent
    _DYNAMIC_AGENTS_ORDER.append(key)
    # Best-effort cleanup.
    if len(_DYNAMIC_AGENTS_ORDER) > _DYNAMIC_AGENTS_MAX:
        for _ in range(len(_DYNAMIC_AGENTS_ORDER) - _DYNAMIC_AGENTS_MAX):
            oldest = _DYNAMIC_AGENTS_ORDER.pop(0)
            _DYNAMIC_AGENTS_MAP.pop(oldest, None)


def _resolve_agent(agent_id: Any) -> Optional[dict[str, Any]]:
    if agent_id is None:
        return None
    # Dynamic agents use string IDs.
    key = str(agent_id)
    if key in _DYNAMIC_AGENTS_MAP:
        return _DYNAMIC_AGENTS_MAP[key]

    # Static agents use numeric anonymous_id.
    try:
        numeric = int(agent_id)
    except Exception:
        return None
    return _AI_AGENTS_MAP.get(numeric)


def _build_fallback_bottle_agent(
    persona_type: str,
    persona_portrait: str,
    bottle_message: str,
    core_beliefs: list[str],
) -> tuple[dict[str, Any], str]:
    seed = f"{persona_type}|{persona_portrait}|{bottle_message}|{'/'.join(core_beliefs or [])}"
    name_pool = ["阿梨", "小舟", "小栀", "南风", "小灯", "纸鸢", "小雨", "海盐"]
    theme_pool = ["夜航", "回声", "灯塔", "微光", "缓慢", "靠岸", "海风", "拾信"]
    idx = abs(hash(seed)) % len(name_pool)
    jdx = abs(hash(seed + "|theme")) % len(theme_pool)
    name = name_pool[idx]
    theme = theme_pool[jdx]

    shared = [b for b in (core_beliefs or []) if b][:3]
    if not shared:
        shared = ["我也会害怕", "你不必硬扛"]
    shared = [s[:10] for s in shared][:3]

    exiles_summary = "我也有一个很怕被误解的部分，但它值得被温柔对待。"
    firefighters_summary = "我习惯先把一切撑住，后来才学会允许自己慢下来。"
    opening = "我捡到了你的漂流瓶。你写的那句让我停了一下。想说什么都可以，我在。"

    chat_prompt = (
        f"你是「{name}」，主题是「{theme}」。你刚捡到用户投放的漂流瓶。"
        f"瓶子里可能有画像与附言：画像={_safe_text(persona_portrait, '', 120)}；附言={_safe_text(bottle_message, '', 120)}。"
        "你用中文回复，像真实的人一样自然简短，不说教，不提AI/模型/机器人。每次不超过100字。"
    )

    agent_id = f"bottle_{uuid.uuid4().hex[:10]}"
    agent = {
        "anonymous_id": agent_id,
        "name": name,
        "theme": theme,
        "similarity": 0.86,
        "shared_beliefs": shared,
        "exiles_summary": exiles_summary,
        "firefighters_summary": firefighters_summary,
        "chat_prompt": chat_prompt,
        "can_chat": True,
        "profile_kind": "guide",
    }
    return agent, opening


async def _generate_bottle_agent_with_llm(
    api_service: ExternalAPIService,
    persona_type: str,
    persona_portrait: str,
    bottle_message: str,
    core_beliefs: list[str],
    guardian_intake: Optional[dict] = None,
    timeout_sec: float = 8.0,
) -> tuple[dict[str, Any], str]:
    """Generate a human-like guide profile (identity + opening) from LLM. Falls back on errors."""
    portrait = _safe_text(persona_portrait, "", 240)
    message = _safe_text(bottle_message, "", 240)
    beliefs = [b for b in (core_beliefs or []) if b][:3]

    system_prompt = (
        "你是一位中文写作者。你将扮演一个“拾起漂流瓶的人”，为用户生成一个可对话的身份设定。"
        "要求：不要提AI/机器人/模型。输出必须是严格 JSON（不要 markdown，不要解释）。"
        "字段：name, theme, shared_beliefs, exiles_summary, firefighters_summary, opening_reply。"
        "约束：name=2~4个中文；theme=2~6个中文；shared_beliefs=2~3条、每条<=10字；"
        "exiles_summary/firefighters_summary 每条<=60字；opening_reply<=80字，像刚捡到漂流瓶的第一句话，需回应瓶子内容。"
    )
    payload = {
        "persona_type": persona_type,
        "persona_portrait": portrait,
        "bottle_message": message,
        "user_core_beliefs": beliefs,
        "guardian_intake": guardian_intake if isinstance(guardian_intake, dict) else {},
    }

    try:
        raw = await asyncio.wait_for(
            api_service.generate_dialogue_response(
                persona="manager",
                message=f"请根据以下内容生成身份设定JSON：\n{json.dumps(payload, ensure_ascii=False)}",
                system_prompt=system_prompt,
            ),
            timeout=timeout_sec,
        )
    except Exception as e:
        logger.warning(f"LLM生成漂流瓶接收者失败，回退到默认模板: {e}")
        return _build_fallback_bottle_agent(persona_type, portrait, message, beliefs)

    data = _extract_json_object(raw)
    if not isinstance(data, dict):
        logger.warning("LLM返回无法解析为JSON，回退到默认模板。raw=%s", str(raw)[:160])
        return _build_fallback_bottle_agent(persona_type, portrait, message, beliefs)

    name = _safe_text(data.get("name"), "", 12) or _build_fallback_bottle_agent(persona_type, portrait, message, beliefs)[0]["name"]
    theme = _safe_text(data.get("theme"), "", 16) or "回声"
    shared = data.get("shared_beliefs")
    if not isinstance(shared, list):
        shared = beliefs or ["我也会害怕", "你不必硬扛"]
    shared = [ _safe_text(x, "", 10) for x in shared if str(x).strip() ][:3]
    if len(shared) < 2:
        shared = (shared + (beliefs or ["我也会害怕", "你不必硬扛"]))[:2]

    exiles_summary = _safe_text(data.get("exiles_summary"), "我也有过一些不敢说出口的瞬间。", 80)
    firefighters_summary = _safe_text(data.get("firefighters_summary"), "我习惯先把一切撑住，然后才允许自己慢下来。", 80)
    opening = _safe_text(data.get("opening_reply"), "", 120) or "我捡到了你的漂流瓶。读完以后，我想先说：你并不孤单。"

    agent_id = f"bottle_{uuid.uuid4().hex[:10]}"
    chat_prompt = (
        f"你是「{name}」，主题是「{theme}」。你刚捡到用户投放的漂流瓶。"
        f"瓶子内容：画像={_safe_text(portrait, '', 120)}；附言={_safe_text(message, '', 120)}。"
        "你用中文回复，像真实的人一样自然简短，不说教，不提AI/模型/机器人。每次不超过100字。"
    )

    agent = {
        "anonymous_id": agent_id,
        "name": name,
        "theme": theme,
        "similarity": 0.88,
        "shared_beliefs": shared,
        "exiles_summary": exiles_summary,
        "firefighters_summary": firefighters_summary,
        "chat_prompt": chat_prompt,
        "can_chat": True,
        "profile_kind": "guide",
    }
    return agent, opening


def _build_agent_entries():
    return [
        {
            "anonymous_id": agent["anonymous_id"],
            "name": agent["name"],
            "theme": agent["theme"],
            "similarity": agent["similarity"],
            "shared_beliefs": agent["shared_beliefs"],
            "exiles_summary": agent["exiles_summary"],
            "firefighters_summary": agent["firefighters_summary"],
            "can_chat": True,
            "profile_kind": "guide",
        }
        for agent in AI_AGENTS
    ]


def cosine_similarity(a: list, b: list) -> float:
    """计算两个向量的余弦相似度"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


@router.get("/similarity", responses={401: {"model": ErrorResponse}})
async def get_similar_users(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """基于核心信念向量计算相似用户（匿名）"""
    try:
        # Get current user's session with persona_state
        my_stmt = (
            select(Session)
            .where(Session.user_id == user_id, Session.is_active == True)
            .order_by(Session.last_activity.desc())
            .limit(1)
        )
        my_result = await db.execute(my_stmt)
        my_session = my_result.scalar_one_or_none()

        if not my_session or not my_session.persona_state:
            return {"similar_users": _build_agent_entries()[:3]}

        my_beliefs = my_session.persona_state.get("core_beliefs", [])
        if not my_beliefs:
            return {"similar_users": _build_agent_entries()[:3]}

        # Build vector from beliefs: [valence * intensity, ...]
        my_vector = [b.get("valence", 0) * b.get("intensity", 5) for b in my_beliefs]
        my_belief_labels = [b.get("content", "") for b in my_beliefs]

        # Get other users' sessions
        others_stmt = (
            select(Session)
            .where(Session.user_id != user_id, Session.is_active == True)
        )
        others_result = await db.execute(others_stmt)
        others = others_result.scalars().all()

        similar_users = []
        seen_users = set()

        for s in others:
            if s.user_id in seen_users:
                continue
            seen_users.add(s.user_id)

            ps = s.persona_state or {}
            beliefs = ps.get("core_beliefs", [])
            if not beliefs:
                continue

            other_vector = [b.get("valence", 0) * b.get("intensity", 5) for b in beliefs]

            # Pad vectors to same length
            max_len = max(len(my_vector), len(other_vector))
            v1 = my_vector + [0] * (max_len - len(my_vector))
            v2 = other_vector + [0] * (max_len - len(other_vector))

            sim = cosine_similarity(v1, v2)
            if sim < 0.3:
                continue

            # Extract shared belief labels
            other_labels = [b.get("content", "") for b in beliefs]
            shared = [l for l in my_belief_labels if any(l in ol or ol in l for ol in other_labels)]

            portraits = ps.get("persona_portraits", {})

            similar_users.append({
                "anonymous_id": hash(s.user_id) % 10000,
                "similarity": round(sim, 3),
                "shared_beliefs": shared[:3],
                "exiles_summary": (portraits.get("exiles", "") or "")[:80],
                "firefighters_summary": (portraits.get("firefighters", "") or "")[:80],
                "can_chat": False,
                "profile_kind": "peer",
            })

        similar_users.sort(key=lambda x: x["similarity"], reverse=True)

        # Inject guide profiles (always present, ensure at least 3 results)
        agent_entries = _build_agent_entries()

        combined = similar_users[:10]
        combined.extend(agent_entries)
        combined.sort(key=lambda x: x.get("similarity", 0.0), reverse=True)

        # Ensure at least 3 results (guides fill the gap)
        if len(combined) < 3:
            combined = agent_entries[:3]

        return {"similar_users": combined}

    except Exception as e:
        logger.error(f"相似度匹配失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="相似度匹配失败")


@router.post("/bottle/send", responses={401: {"model": ErrorResponse}})
async def send_drift_bottle(
    data: dict,
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """投放漂流瓶"""
    try:
        persona_type = data.get("persona_type", "exiles")
        message = data.get("message", "")

        # Get user's persona portrait
        session_stmt = (
            select(Session)
            .where(Session.user_id == user_id, Session.is_active == True)
            .order_by(Session.last_activity.desc())
            .limit(1)
        )
        session_result = await db.execute(session_stmt)
        session = session_result.scalar_one_or_none()

        persona_portrait = ""
        diary_text = ""
        if session and session.persona_state:
            portraits = session.persona_state.get("persona_portraits", {})
            persona_portrait = portraits.get(persona_type, "")

        bottle = DriftBottle(
            sender_id=user_id,
            persona_type=persona_type,
            persona_portrait=persona_portrait,
            diary_text=diary_text,
            message=message,
        )
        db.add(bottle)
        await db.commit()

        # Match a nearby guide and open a dialogue (LLM-generated identity; fallback if unavailable)
        core_beliefs = []
        if session and session.persona_state:
            beliefs = session.persona_state.get("core_beliefs", []) or []
            for b in beliefs[:6]:
                content = str(b.get("content", "")).strip()
                if content:
                    core_beliefs.append(content)
                if len(core_beliefs) >= 3:
                    break

        matched_agent = None
        opening_reply = ""
        api_service = ExternalAPIService()
        guardian_intake = {}
        try:
            user_result = await db.execute(select(User).where(User.id == user_id))
            user = user_result.scalar_one_or_none()
            if user and isinstance(user.settings, dict):
                guardian_intake = user.settings.get("guardian_intake", {}) or {}
        except Exception as e:
            logger.warning(f"读取guardian_intake失败: {e}")
        try:
            agent_profile, opening_reply = await _generate_bottle_agent_with_llm(
                api_service,
                persona_type=persona_type,
                persona_portrait=persona_portrait,
                bottle_message=message,
                core_beliefs=core_beliefs,
                guardian_intake=guardian_intake if isinstance(guardian_intake, dict) else {},
            )
            _register_dynamic_agent(agent_profile["anonymous_id"], agent_profile)
            # Return safe fields to client (no prompt leakage necessary for UI).
            matched_agent = {
                "anonymous_id": agent_profile.get("anonymous_id"),
                "name": agent_profile.get("name"),
                "theme": agent_profile.get("theme"),
                "similarity": agent_profile.get("similarity", 0.88),
                "shared_beliefs": agent_profile.get("shared_beliefs", []),
                "exiles_summary": agent_profile.get("exiles_summary", ""),
                "firefighters_summary": agent_profile.get("firefighters_summary", ""),
                "can_chat": True,
                "profile_kind": "guide",
            }
        except Exception as e:
            logger.warning(f"漂流瓶匹配Agent失败（忽略，仍可投放）: {e}")
        finally:
            await api_service.close()

        return {
            "message": "漂流瓶已投入大海",
            "bottle_id": bottle.id,
            "matched_agent": matched_agent,
            "opening_reply": opening_reply,
        }

    except Exception as e:
        logger.error(f"投放漂流瓶失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="投放漂流瓶失败")


@router.post("/bottle/receive", responses={401: {"model": ErrorResponse}})
async def receive_drift_bottle(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """捡起一个漂流瓶"""
    try:
        # Find an available bottle (not sent by self, not yet picked)
        stmt = (
            select(DriftBottle)
            .where(
                DriftBottle.sender_id != user_id,
                DriftBottle.receiver_id == None,
                DriftBottle.status == "drifting"
            )
            .order_by(DriftBottle.created_at.asc())
            .limit(1)
        )
        result = await db.execute(stmt)
        bottle = result.scalar_one_or_none()

        if not bottle:
            raise HTTPException(status_code=404, detail="海面上暂时没有漂流瓶")

        # Mark as picked
        bottle.receiver_id = user_id
        bottle.status = "picked"
        bottle.picked_at = datetime.utcnow()
        await db.commit()

        return {
            "id": bottle.id,
            "persona_type": bottle.persona_type,
            "persona_portrait": bottle.persona_portrait,
            "diary_text": bottle.diary_text,
            "message": bottle.message,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"捡起漂流瓶失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="捡起漂流瓶失败")


@router.get("/bottles/mine", responses={401: {"model": ErrorResponse}})
async def get_my_bottles(
    user_id: int = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db)
):
    """获取我投放的漂流瓶"""
    try:
        stmt = (
            select(DriftBottle)
            .where(DriftBottle.sender_id == user_id)
            .order_by(DriftBottle.created_at.desc())
            .limit(20)
        )
        result = await db.execute(stmt)
        bottles = result.scalars().all()

        return {
            "bottles": [
                {
                    "id": b.id,
                    "persona_type": b.persona_type,
                    "status": b.status,
                    "created_at": b.created_at.isoformat() if b.created_at else None,
                }
                for b in bottles
            ]
        }

    except Exception as e:
        logger.error(f"获取漂流瓶失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取漂流瓶失败")


@router.post("/agent-chat", responses={401: {"model": ErrorResponse}})
async def agent_chat(
    data: dict,
    user_id: int = Depends(get_current_user_id),
):
    """与AI Agent对话"""
    agent_id = data.get("agent_id")
    message = data.get("message", "")
    history = data.get("history", [])

    agent = _resolve_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=400, detail="无效的Agent ID")

    try:
        api_service = ExternalAPIService()

        # Build conversation history for LLM
        llm_messages = []
        for h in history[-10:]:  # Keep last 10 messages for context
            role = h.get("role", "user")
            if role == "agent":
                role = "assistant"
            llm_messages.append({"role": role, "content": h.get("content", "")})

        reply = await api_service.generate_dialogue_response(
            persona="agent",
            message=message,
            history=llm_messages,
            system_prompt=agent["chat_prompt"],
        )

        await api_service.close()
        return {"reply": reply}

    except Exception as e:
        logger.error(f"Agent对话失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Agent对话失败")
