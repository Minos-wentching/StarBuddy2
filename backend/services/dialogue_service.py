"""
对话服务

处理用户消息，协调情绪分析、人格状态机和对话生成
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from ..services.external_apis import ExternalAPIService
from ..services.version_service import VersionService
from ..services.council_service import CouncilService
from ..services.counselor_service import CounselorService
from ..services.manager_service import ManagerService
from ..services.memory_service import MemoryStore
from ..services.prompts import EXILES_DIARY_PROMPT_TEMPLATE, FIREFIGHTERS_DIARY_PROMPT_TEMPLATE
from ..services.reference_library import find_reference_snippets, format_snippets_for_prompt

from ..models.schemas import DialogueResponse, CounselorReport, ManagerDecision
from ..database.models import DialogueHistory, Session, HealingImage, User
from ..api.sse_endpoints import connection_manager
from sqlalchemy import select, delete, update
from ..api_config import config

logger = logging.getLogger(__name__)


class DialogueService:
    """对话服务 (Aligned with Multiego Orchestrator logic)"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.external_apis = ExternalAPIService()
        self.counselor = CounselorService(self.external_apis)
        self.manager = ManagerService(self.external_apis)
        # 缓存当前 ManagerDecision，用于日记生成
        self._current_decision: Optional[ManagerDecision] = None

    async def process_message(
        self,
        session_id: str,
        message: str,
        background_tasks: BackgroundTasks,
        user_id: Optional[str] = None
    ) -> DialogueResponse:
        """处理用户消息，流程对齐 Multiego：Manager 先回复，再分析与切换"""
        try:
            # 1. 获取会话
            session_stmt = select(Session).where(Session.id == session_id)
            session_result = await self.db.execute(session_stmt)
            session = session_result.scalar_one_or_none()
            if not session:
                raise ValueError(f"Session not found: {session_id}")

            # 1.1 用户 settings（用于监护人补充信息等）
            user_settings: dict = {}
            try:
                user_result = await self.db.execute(select(User).where(User.id == session.user_id))
                user = user_result.scalar_one_or_none()
                if user:
                    user_settings = dict(user.settings or {})
            except Exception as e:
                logger.warning(f"读取用户settings失败: {e}")

            # 2. 历史上下文（保持与 Multiego 一致：chat_history[-8:]）
            history_turns = await self.get_history(session_id, limit=8)
            history_turns = list(reversed(history_turns))
            chat_history = self._build_chat_history(history_turns)

            # 3. 用户背景信息
            persona_state = session.persona_state or {}
            existing_facts = persona_state.get("user_facts", [])
            user_background = self._build_user_background(existing_facts) + self._build_guardian_intake_context(user_settings)
            try:
                ref_snips = find_reference_snippets(message)
                ref_text = format_snippets_for_prompt(ref_snips)
                if ref_text:
                    user_background = f"{user_background}\n\n{ref_text}"
            except Exception as e:
                logger.warning(f"本地参考资料检索失败（忽略）: {e}")

            # 4. 始终由 Manager 回复（Only Manager chats）
            manager_reply = await self.manager.chat(
                user_input=message,
                history=chat_history[-8:] if chat_history else None,
                user_background=user_background + self._build_profile_context(persona_state),
                active_agent=session.current_persona or "manager",
            )

            # 5. 提取并持久化用户事实（先于分析，贴近 Multiego）
            merged_facts = await self._extract_user_facts(message, existing_facts)

            # 6. Counselor 分析（使用最近6条 chat history 作为记忆文本）
            analysis_history = chat_history[-6:] if chat_history else []
            history_text = "\n".join(f"{m['role']}: {m['content']}" for m in analysis_history)
            profile_context = self._build_profile_context(persona_state)
            if profile_context:
                history_text = f"{profile_context}\n\n{history_text}" if history_text else profile_context
            counselor_report = await self.counselor.analyze_trauma(message, history_text)

            # 7. 记忆存储（对齐 Multiego：store_report + store_memory）
            memory_store = MemoryStore()
            if self.external_apis.client:
                memory_store.set_llm_client(self.external_apis.client)
            if counselor_report:
                background_tasks.add_task(
                    memory_store.store_report, counselor_report.dict(), message, session.user_id
                )
            background_tasks.add_task(
                memory_store.store_memory,
                f"User: {message}\nAssistant: {manager_reply}",
                {"session_id": session_id, "user_id": session.user_id}
            )

            # 8. 计算强度（Multiego：基于 core belief + 次人格衰减）
            turn_count = int(persona_state.get("turn_count", 0)) + 1
            persona_switch_turn = int(persona_state.get("persona_switch_turn", 0))
            intensity = self._compute_intensity(
                counselor_report=counselor_report,
                previous_intensity=float(session.emotion_intensity or 0.0),
                current_persona=session.current_persona or "manager",
                turn_count=turn_count,
                persona_switch_turn=persona_switch_turn,
            )

            previous_clarity = float(persona_state.get("self_presence_clarity", 0.6) or 0.6)
            previous_compassion = float(persona_state.get("self_presence_compassion", 0.6) or 0.6)
            self_presence = self._compute_self_presence(
                counselor_report=counselor_report,
                intensity=intensity,
                current_persona=session.current_persona or "manager",
                previous_clarity=previous_clarity,
                previous_compassion=previous_compassion,
            )

            current_persona = session.current_persona or "manager"
            was_manager = current_persona == "manager"

            # SSE 推送 CounselorReport
            if counselor_report.core_beliefs:
                background_tasks.add_task(
                    connection_manager.send_event, session_id, {
                        "event_type": "counselor_report",
                        "data": {
                            "core_beliefs": [
                                {"content": b.content, "valence": b.valence, "intensity": b.intensity}
                                for b in counselor_report.core_beliefs
                            ],
                            "trigger_event": counselor_report.trigger_event,
                            "emotional_summary": counselor_report.emotional_summary,
                            "self_presence": {
                                "clarity": self_presence["clarity"],
                                "compassion": self_presence["compassion"],
                                "delta_clarity": self_presence["delta_clarity"],
                                "delta_compassion": self_presence["delta_compassion"],
                                "trend": self_presence["trend"],
                                "analysis": self_presence["analysis"],
                            },
                        }
                    }
                )

            # 9. 按阈值切换（Multiego）
            response_text = manager_reply
            council_active = False
            council_task_id = None
            switched_persona = current_persona
            manager_decision = None

            if was_manager and intensity > config.INTENSITY_SWITCH_THRESHOLD:
                logger.info(f"Triggering personality switch: session={session_id}, intensity={intensity:.3f}")
                manager_decision = await self.manager.decide(
                    counselor_report=counselor_report,
                    chat_history=chat_history[-4:] if chat_history else None
                )
                self._current_decision = manager_decision
                council_topic = (
                    manager_decision.council_topic
                    or counselor_report.emotional_summary
                    or "当前情绪"
                )
                council_active = True
                council_task_id = await self._start_inner_council(
                    session_id, council_topic, None, background_tasks
                )
                switched_persona = manager_decision.target_agent.value

                # 仅在切换到次人格时写日记（Multiego）
                diary_meta = await self._generate_diary_entry(
                    session_id=session_id,
                    persona=switched_persona,
                    user_input=message,
                    report=counselor_report,
                    manager_decision=manager_decision,
                    user_id=session.user_id,
                    persona_state=persona_state,
                )
                if isinstance(diary_meta, dict) and diary_meta.get("trigger_event"):
                    event_context = dict((persona_state or {}).get("event_context") or {})
                    history_rows = event_context.get("event_history", []) if isinstance(event_context.get("event_history", []), list) else []
                    history_rows.append({
                        "event_id": diary_meta.get("event_id", ""),
                        "trigger_event": diary_meta.get("trigger_event", ""),
                        "trauma_event": diary_meta.get("trauma_event", ""),
                        "event_source": diary_meta.get("event_source", ""),
                        "timestamp": datetime.utcnow().isoformat(),
                    })
                    event_context.update({
                        "active_event_id": diary_meta.get("event_id", ""),
                        "active_trigger_event": diary_meta.get("trigger_event", ""),
                        "active_trauma_event": diary_meta.get("trauma_event", ""),
                        "active_event_source": diary_meta.get("event_source", ""),
                        "event_history": history_rows[-20:],
                    })
                    persona_state = dict(persona_state or {})
                    persona_state["event_context"] = event_context

                background_tasks.add_task(
                    connection_manager.send_event, session_id, {
                        "event_type": "persona_switch",
                        "data": {
                            "persona": switched_persona,
                            "intensity": intensity,
                            "reason": "threshold_switch",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )

                background_tasks.add_task(
                    connection_manager.send_event, session_id, {
                        "event_type": "manager_decision",
                        "data": {
                            "target_agent": manager_decision.target_agent.value,
                            "events": manager_decision.events,
                            "character_profile": manager_decision.character_profile,
                            "reasoning": manager_decision.reasoning,
                        }
                    }
                )
            elif (not was_manager) and intensity <= config.INTENSITY_RETURN_THRESHOLD:
                switched_persona = "manager"
                persona_switch_turn = 0
                background_tasks.add_task(
                    connection_manager.send_event, session_id, {
                        "event_type": "persona_switch",
                        "data": {
                            "persona": "manager",
                            "intensity": intensity,
                            "reason": "return_threshold",
                            "timestamp": datetime.utcnow().isoformat()
                        }
                    }
                )

            if switched_persona in ["exiles", "firefighters"] and was_manager:
                persona_switch_turn = turn_count

            # 10. 持久化会话状态
            new_persona_state = dict(persona_state)
            if "event_context" not in new_persona_state:
                new_persona_state["event_context"] = {
                    "active_event_id": "",
                    "active_trigger_event": "",
                    "active_trauma_event": "",
                    "active_event_source": "",
                    "event_history": [],
                }
            new_persona_state["user_facts"] = merged_facts
            new_persona_state["turn_count"] = turn_count
            new_persona_state["persona_switch_turn"] = persona_switch_turn
            new_persona_state["self_presence_clarity"] = self_presence["clarity"]
            new_persona_state["self_presence_compassion"] = self_presence["compassion"]
            new_persona_state["self_presence_trend"] = self_presence["trend"]
            await self.db.execute(
                update(Session).where(Session.id == session_id).values(
                    persona_state=new_persona_state,
                    current_persona=switched_persona,
                    emotion_intensity=intensity,
                )
            )
            await self.db.commit()

            # 11. 保存对话历史（assistant 始终是 manager）
            await self._save_dialogue_history(
                session_id=session_id,
                message=message,
                response=response_text,
                persona="manager",
                intensity=intensity,
            )

            # 12. 创建快照
            version_info = await self._create_snapshot(session_id, {
                "persona": switched_persona,
                "intensity": intensity,
                "self_presence_clarity": self_presence["clarity"],
                "self_presence_compassion": self_presence["compassion"],
                "counselor_report": str(counselor_report)
            })

            return DialogueResponse(
                response=response_text,
                persona="manager",
                emotion_intensity=intensity,
                council_active=council_active,
                council_task_id=council_task_id,
                version_info=version_info,
                timestamp=datetime.utcnow()
            )

        except Exception as e:
            logger.error(f"Error in process_message: {e}", exc_info=True)
            return DialogueResponse(
                response="对不起，我内部处理出现了一些波动，请稍后再试。",
                persona="manager",
                emotion_intensity=0.5,
                timestamp=datetime.utcnow()
            )

    async def _extract_user_facts(self, user_input: str, existing_facts: List[str]) -> List[str]:
        """提取用户事实并返回合并结果"""
        try:
            new_facts = await self.counselor.extract_user_facts(user_input, existing_facts)
            if new_facts:
                all_facts = list(set(existing_facts + new_facts))
                logger.info(f"Updated user facts: {new_facts}")
                return all_facts
            return existing_facts
        except Exception as e:
            logger.error(f"Failed to update user facts: {e}")
            return existing_facts

    async def _generate_diary_entry(
        self,
        session_id: str,
        persona: str,
        user_input: str,
        report: CounselorReport,
        manager_decision: Optional[ManagerDecision] = None,
        user_id: Optional[int] = None,
        persona_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        异步生成日记和图像，持久化到 DB。
        移植自 Multiego orchestrator._write_diary，使用 per-agent 日记 prompt。
        现在支持 ManagerDecision 中的 events 和 character_profile 作为 persona_hint。
        """
        try:
            # 构建 belief_summary
            belief_summary = ""
            if report and report.core_beliefs:
                belief_summary = "；".join(b.content for b in report.core_beliefs)

            # 触发事件优先级：记忆球记忆 > manager_decision.events > counselor.trigger_event > 用户原话片段 > 默认
            memory_orb_event = await self._resolve_memory_orb_event(
                user_input=user_input,
                report=report,
                user_id=user_id,
            )
            fallback_user_event = self._build_user_input_event_fallback(user_input)

            session_event_context = (persona_state or {}).get("event_context", {}) if isinstance((persona_state or {}).get("event_context", {}), dict) else {}
            session_active_event = str(session_event_context.get("active_trauma_event", "") or session_event_context.get("active_trigger_event", "") or "").strip()

            trigger_event = (
                session_active_event
                or memory_orb_event
                or (manager_decision.events if manager_decision and manager_decision.events else "")
                or (report.trigger_event if report and report.trigger_event else "")
                or fallback_user_event
                or "未明确触发事件，请从用户原话提炼一个具体瞬间"
            )
            event_source = (
                "session_event_context"
                if session_active_event
                else "memory_orb_memory"
                if memory_orb_event
                else "manager_decision_events"
                if (manager_decision and manager_decision.events)
                else "counselor_trigger_event"
                if (report and report.trigger_event)
                else "user_input_excerpt"
                if fallback_user_event
                else "default_fallback"
            )
            fallback_level = (
                1 if session_active_event else
                2 if memory_orb_event else
                3 if (manager_decision and manager_decision.events) else
                4 if (report and report.trigger_event) else
                5 if fallback_user_event else
                6
            )


            # 构建 persona_hint (移植自 Multiego，使用 ManagerDecision)
            persona_hint = ""
            if manager_decision:
                persona_hint = self.manager.build_persona_hint(manager_decision)
            elif report and report.trigger_event:
                persona_hint = f"\n\n【触发事件】\n{report.trigger_event}"

            # 获取 RAG 上下文
            rag_context = ""
            try:
                memory_store = MemoryStore()
                memory_store.set_llm_client(self.external_apis.client)
                query = ""
                if manager_decision and manager_decision.events:
                    query = manager_decision.events
                elif report:
                    query = report.trigger_event or report.emotional_summary
                if query:
                    rag_results = await memory_store.hybrid_search(query, n_results=5, user_id=user_id)
                    rag_context = MemoryStore.format_rag_context(rag_results)
            except Exception as e:
                logger.warning(f"RAG context retrieval failed: {e}")

            # 构建 per-agent 日记 prompt（与 Multiego 文案保持一致）
            if persona == "exiles":
                diary_prompt = EXILES_DIARY_PROMPT_TEMPLATE.format(
                    belief_summary=belief_summary or "待探索",
                    event_source=event_source,
                    trigger_event=trigger_event,
                    user_input=user_input,
                )
            elif persona == "firefighters":
                diary_prompt = FIREFIGHTERS_DIARY_PROMPT_TEMPLATE.format(
                    belief_summary=belief_summary or "待探索",
                    event_source=event_source,
                    trigger_event=trigger_event,
                    user_input=user_input,
                )
            else:
                return

            if persona_hint:
                diary_prompt += persona_hint
            if rag_context:
                diary_prompt += f"\n\n{rag_context}"

            logger.info(
                "Diary event selection | session=%s persona=%s source=%s level=%s event=%s beliefs=%s",
                session_id,
                persona,
                event_source,
                fallback_level,
                trigger_event[:80],
                len(report.core_beliefs) if report and report.core_beliefs else 0,
            )

            # 生成日记文本
            custom_system_prompt = ""
            state = persona_state or {}
            if persona == "exiles":
                custom_system_prompt = state.get("exiles_system_prompt", "")
            elif persona == "firefighters":
                custom_system_prompt = state.get("firefighters_system_prompt", "")

            diary_text = await self.external_apis.generate_dialogue_response(
                persona=persona,
                message=diary_prompt,
                context={"counselor_report": report.emotional_summary if report else ""},
                system_prompt=custom_system_prompt or None,
            )

            # 生成意象图像
            image_result = await self.external_apis.generate_imagery(diary_text[:100])
            image_url = None
            if image_result:
                results = image_result.get("results", [])
                if results:
                    image_url = results[0].get("url")

            # 持久化到 DB
            if image_url or diary_text:
                healing_image = HealingImage(
                    session_id=session_id,
                    image_url=image_url or "",
                    diary_text=diary_text,
                    persona=persona,
                )
                self.db.add(healing_image)
                await self.db.commit()

            # 存储日记到 ChromaDB
            try:
                belief_ref = report.core_beliefs[0].belief_id if report and report.core_beliefs else ""

                memory_store.store_diary(diary_text, persona, belief_ref, user_id=user_id)
            except Exception as e:
                logger.warning(f"Failed to store diary to ChromaDB: {e}")

            # SSE 推送
            await connection_manager.send_event(session_id, {
                "event_type": "diary_update",
                "data": {
                    "text": diary_text,
                    "image_url": image_url,
                    "persona": persona,
                }
            })
            logger.info(f"Diary entry generated for session {session_id}, persona={persona}")
            return {
                "event_id": str(session_event_context.get("active_event_id", "") or ""),
                "trigger_event": trigger_event,
                "trauma_event": trigger_event,
                "event_source": event_source,
                "fallback_level": fallback_level,
                "diary_event_text_preview": trigger_event[:80],
                "diary_context_belief_count": len(report.core_beliefs) if report and report.core_beliefs else 0,
            }
        except Exception as e:
            logger.error(f"Failed to generate diary: {e}")
            return {}

    def _extract_trigger_from_memory_document(self, document: str) -> str:
        text = str(document or "")
        if not text:
            return ""

        trigger_match = re.search(r"(?:^|\n)Trigger:\s*(.+?)(?:\n|$)", text)
        if trigger_match:
            candidate = trigger_match.group(1).strip()
            if candidate:
                return candidate

        origin_match = re.search(r"(?:^|\n)Origin:\s*(.+?)(?:\n|$)", text)
        if origin_match:
            candidate = origin_match.group(1).strip()
            if candidate:
                return candidate

        user_said_match = re.search(r"(?:^|\n)User\s*said:\s*(.+?)(?:\n|$)", text, flags=re.IGNORECASE)
        if user_said_match:
            candidate = user_said_match.group(1).strip()
            if candidate:
                return candidate

        lines = [line.strip() for line in text.splitlines() if line.strip()]
        if lines:
            return lines[0][:80]
        return ""

    async def _resolve_memory_orb_event(
        self,
        user_input: str,
        report: Optional[CounselorReport],
        user_id: Optional[int] = None,
    ) -> str:
        """从记忆库提取最相关的“记忆球事件”文本。"""
        try:
            memory_store = MemoryStore()
            if self.external_apis.client:
                memory_store.set_llm_client(self.external_apis.client)

            query = ""
            if report and report.trigger_event:
                query = report.trigger_event
            elif report and report.emotional_summary:
                query = report.emotional_summary
            else:
                query = (user_input or "")[:120]

            if not query:
                return ""

            hits = await memory_store.hybrid_search(query, n_results=8, user_id=user_id)
            trauma_hits = [item for item in hits if (item.get("metadata") or {}).get("type") == "trauma_event"]
            belief_hits = [item for item in hits if (item.get("metadata") or {}).get("type") == "core_belief"]

            for item in trauma_hits:
                metadata = item.get("metadata", {}) or {}
                event_text = str(metadata.get("trauma_event") or metadata.get("trigger_event") or "").strip()
                if not event_text:
                    event_text = self._extract_trigger_from_memory_document(item.get("document", ""))
                if event_text:
                    return event_text

            for item in belief_hits:
                event_text = self._extract_trigger_from_memory_document(item.get("document", ""))
                if event_text:
                    return event_text

            # 兜底：直接从全部 core_belief 中选最近一条可解析事件
            all_beliefs = memory_store.get_all_beliefs(user_id=user_id)
            if all_beliefs:
                sorted_beliefs = sorted(
                    all_beliefs,
                    key=lambda item: str((item.get("metadata") or {}).get("timestamp", "")),
                    reverse=True,
                )
                for entry in sorted_beliefs[:5]:
                    event_text = self._extract_trigger_from_memory_document(entry.get("document", ""))
                    if event_text:
                        return event_text
        except Exception as e:
            logger.warning("Resolve memory-orb event failed: %s", e)

        return ""

    def _build_user_input_event_fallback(self, user_input: str) -> str:
        text = str(user_input or "").strip()
        if not text:
            return ""
        return text[:60]

    def _compute_self_presence(
        self,
        counselor_report: CounselorReport,
        intensity: float,
        current_persona: str,
        previous_clarity: float,
        previous_compassion: float,
    ) -> Dict[str, Any]:
        """计算 Self-presence 快变量（不参与决策，仅用于观察波动）"""
        trigger_penalty = 0.08 if counselor_report and counselor_report.trigger_event else 0.0
        negative_bias = 0.0
        if counselor_report and counselor_report.core_beliefs:
            negatives = [b for b in counselor_report.core_beliefs if float(getattr(b, "valence", 0.0)) < 0]
            negative_bias = min(0.12, 0.03 * len(negatives))

        persona_penalty = 0.06 if current_persona in ["exiles", "firefighters"] else 0.0

        target_clarity = max(0.0, min(1.0, 0.88 - intensity * 0.58 - trigger_penalty - persona_penalty))
        target_compassion = max(0.0, min(1.0, 0.82 - intensity * 0.34 - negative_bias - persona_penalty * 0.5))

        clarity = max(0.0, min(1.0, previous_clarity * 0.6 + target_clarity * 0.4))
        compassion = max(0.0, min(1.0, previous_compassion * 0.6 + target_compassion * 0.4))

        delta_clarity = clarity - previous_clarity
        delta_compassion = compassion - previous_compassion
        total_delta = delta_clarity + delta_compassion
        if total_delta > 0.04:
            trend = "up"
        elif total_delta < -0.04:
            trend = "down"
        else:
            trend = "stable"

        analysis = (
            f"Self-presence波动：自我觉知{clarity:.2f}({delta_clarity:+.2f})，"
            f"自我接纳{compassion:.2f}({delta_compassion:+.2f})，趋势{trend}。"
        )

        return {
            "clarity": round(clarity, 3),
            "compassion": round(compassion, 3),
            "delta_clarity": round(delta_clarity, 3),
            "delta_compassion": round(delta_compassion, 3),
            "trend": trend,
            "analysis": analysis,
        }

    def _build_chat_history(self, history_turns: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """将 turn 结构历史转换为 OpenAI chat_history 格式"""
        messages: List[Dict[str, str]] = []
        for turn in history_turns:
            user_msg = (turn.get("message") or "").strip()
            assistant_msg = (turn.get("response") or "").strip()
            if user_msg:
                messages.append({"role": "user", "content": user_msg})
            if assistant_msg:
                messages.append({"role": "assistant", "content": assistant_msg})
        return messages

    def _build_user_background(self, facts: List[str]) -> str:
        """构建用户背景文本（Multiego 兼容）"""
        if not facts:
            return ""
        facts_text = "\n".join(f"- {f}" for f in facts)
        return f"\n\n【用户背景信息】\n{facts_text}"

    def _build_guardian_intake_context(self, user_settings: Dict[str, Any]) -> str:
        """构建监护人补充信息上下文（用于更贴合的引导与沟通）"""
        settings = user_settings if isinstance(user_settings, dict) else {}
        intake = settings.get("guardian_intake", {})
        if not isinstance(intake, dict):
            return ""

        interests = str(intake.get("child_interests") or "").strip()
        music = str(intake.get("child_music") or "").strip()
        music_url = str(intake.get("music_url") or "").strip()
        music_upload_url = str(intake.get("music_upload_url") or "").strip()

        rows = []
        if interests:
            rows.append(f"- 兴趣爱好/特长：{interests[:200]}")
        if music:
            rows.append(f"- 喜欢的音乐类型/举例：{music[:200]}")
        if music_url:
            rows.append(f"- 音乐链接：{music_url[:200]}")
        if music_upload_url:
            rows.append(f"- 已上传音乐：{music_upload_url[:200]}")

        if not rows:
            return ""

        return "\n\n【监护人补充信息】\n" + "\n".join(rows)

    def _build_profile_context(self, persona_state: Dict[str, Any]) -> str:
        """构建首次问卷画像上下文"""
        if not persona_state:
            return ""

        profile = persona_state.get("onboarding_profile", {})
        if isinstance(profile, dict):
            profile_digest = str(profile.get("profile_digest", "")).strip()
            trauma_hypothesis = str(profile.get("trauma_hypothesis", "")).strip()
            core_info = profile.get("user_core_info", []) if isinstance(profile.get("user_core_info", []), list) else []
            core_beliefs = profile.get("core_beliefs", []) if isinstance(profile.get("core_beliefs", []), list) else []
        else:
            profile_digest = ""
            core_info = persona_state.get("user_core_info", [])
            trauma_hypothesis = persona_state.get("trauma_hypothesis", "")
            core_beliefs = persona_state.get("core_beliefs_seed", [])

        chunks = []
        if profile_digest:
            chunks.append(f"【用户画像摘要】\n{profile_digest[:180]}")
        if core_info:
            chunks.append("【用户核心画像】\n" + "\n".join(f"- {str(x)[:40]}" for x in core_info[:5]))
        if trauma_hypothesis:
            chunks.append(f"【待探索创伤线索】\n{trauma_hypothesis[:120]}")
        if core_beliefs:
            chunks.append("【候选核心信念】\n" + "\n".join(f"- {str(x)[:40]}" for x in core_beliefs[:4]))

        return "\n\n".join(chunks)

    def _compute_intensity(
        self,
        counselor_report: CounselorReport,
        previous_intensity: float,
        current_persona: str,
        turn_count: int,
        persona_switch_turn: int,
    ) -> float:
        """Multiego 强度算法：core_belief 强度 + 次人格状态衰减"""
        if counselor_report and counselor_report.core_beliefs:
            max_intensity = max(b.intensity for b in counselor_report.core_beliefs)
            raw = min(max_intensity / 10.0, 1.0)
        else:
            raw = max(0.0, min(1.0, previous_intensity))

        if current_persona != "manager" and persona_switch_turn > 0:
            turns_since_switch = max(0, turn_count - persona_switch_turn)
            decay_multiplier = max(0.0, 1.0 - turns_since_switch * config.INTENSITY_DECAY_RATE)
            return max(0.0, min(1.0, raw * decay_multiplier))

        return raw

    async def _start_inner_council(
        self,
        session_id: str,
        message: str,
        persona_state,
        background_tasks: BackgroundTasks
    ) -> str:
        """启动内心议会"""
        # 调用议会服务启动议会
        council_service = CouncilService(self.db)
        council = await council_service.start_council(
            session_id=session_id,
            topic=message,  # 使用消息作为议题
            max_rounds=3,   # 默认轮数
            background_tasks=background_tasks
        )
        council_id = council.council_id
        logger.info(f"启动内心议会: {council_id}")
        return council_id

    async def _create_snapshot(self, session_id: str, state_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """创建版本快照"""
        try:
            version_service = VersionService(self.db)
            snapshot = await version_service.create_snapshot(
                session_id=session_id,
                state_data=state_data,
                tags=["dialogue", state_data.get("persona", "unknown")]
            )
            return {
                "version_hash": snapshot.id,
                "created_at": snapshot.created_at,
                "snapshot_id": snapshot.id
            }
        except Exception as e:
            logger.error(f"创建快照失败: {session_id}, 错误: {e}")
            return None

    async def _save_dialogue_history(
        self,
        session_id: str,
        message: str,
        response: str,
        persona: str,
        intensity: float
    ):
        """保存对话历史"""
        try:
            dialogue_history = DialogueHistory(
                session_id=session_id,
                message=message,
                response=response,
                persona=persona,
                emotion_intensity=intensity,
                emotion_analysis={},  # 可以添加情绪分析结果
                created_at=datetime.utcnow()
            )
            self.db.add(dialogue_history)
            await self.db.commit()
            logger.info(f"对话历史保存: {session_id}, 人格: {persona}")
        except Exception as e:
            logger.error(f"保存对话历史失败: {session_id}, 错误: {e}")
            await self.db.rollback()

    async def get_history(self, session_id: str, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """获取对话历史"""
        try:
            stmt = (
                select(DialogueHistory)
                .where(DialogueHistory.session_id == session_id)
                .order_by(DialogueHistory.created_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.db.execute(stmt)
            history_records = result.scalars().all()

            history = []
            for record in history_records:
                history.append({
                    "id": record.id,
                    "session_id": record.session_id,
                    "message": record.message,
                    "response": record.response,
                    "persona": record.persona,
                    "emotion_intensity": record.emotion_intensity,
                    "emotion_analysis": record.emotion_analysis,
                    "created_at": record.created_at
                })

            return history
        except Exception as e:
            logger.error(f"获取对话历史失败: {session_id}, 错误: {e}")
            return []

    async def clear_history(self, session_id: str) -> bool:
        """清空对话历史"""
        try:
            stmt = delete(DialogueHistory).where(DialogueHistory.session_id == session_id)
            result = await self.db.execute(stmt)
            await self.db.commit()
            deleted_count = result.rowcount
            logger.info(f"清空对话历史: {session_id}, 删除记录数: {deleted_count}")
            return True
        except Exception as e:
            logger.error(f"清空对话历史失败: {session_id}, 错误: {e}")
            await self.db.rollback()
            return False

async def example_usage():
    """示例用法"""
    from ..database.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        service = DialogueService(db)

        # 模拟处理消息
        response = await service.process_message(
            session_id="test_session",
            message="我今天感到非常焦虑",
            background_tasks=BackgroundTasks()
        )

        print(f"响应: {response.message}")
        print(f"人格: {response.persona}")
        print(f"情绪强度: {response.emotion_intensity}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())
