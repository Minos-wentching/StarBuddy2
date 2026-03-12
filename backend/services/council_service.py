"""
内心议会服务

管理 Exiles 和 Firefighters 的辩论协调，Counselor整合分析
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
from fastapi import BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models.schemas import CouncilResponse, CouncilRound
from ..services.external_apis import ExternalAPIService
from ..services.counselor_service import CounselorService
from ..database.models import Council
from ..api.sse_endpoints import connection_manager
from ..api_config import config
from ..utils.cache import council_cache

logger = logging.getLogger(__name__)


class CouncilService:
    """内心议会服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.external_apis = ExternalAPIService()

    async def start_council(
        self,
        session_id: str,
        topic: str,
        max_rounds: int = None,
        background_tasks: BackgroundTasks = None
    ) -> CouncilResponse:
        """启动内心议会"""
        # API 密钥检查
        if self.external_apis.client is None:
            logger.warning("DashScope API key not set, council will use mock responses")
        try:
            # 使用配置默认值
            if max_rounds is None:
                max_rounds = config.COUNCIL_NEGOTIATION_ROUNDS

            council_id = f"council_{session_id}_{uuid.uuid4().hex[:8]}"

            # 写入 DB
            council_record = Council(
                id=council_id,
                session_id=session_id,
                debate_data={"topic": topic, "max_rounds": max_rounds, "rounds": []},
                rounds=0,
                status="active",
                started_at=datetime.utcnow(),
            )
            self.db.add(council_record)
            await self.db.commit()
            await self.db.refresh(council_record)

            if background_tasks:
                background_tasks.add_task(self._execute_council, council_id)

            logger.info(f"内心议会启动: {council_id}, 话题: {topic}")

            return CouncilResponse(
                council_id=council_id,
                session_id=session_id,
                status="active",
                current_round=0,
                total_rounds=max_rounds,
                rounds=[],
                conclusion=None,
                started_at=council_record.started_at,
                completed_at=None,
            )
        except Exception as e:
            logger.error(f"启动议会失败: {e}")
            raise

    async def _load_council(self, council_id: str) -> Optional[Council]:
        """从 DB 加载议会记录"""
        result = await self.db.execute(select(Council).where(Council.id == council_id))
        return result.scalar_one_or_none()

    async def get_council(self, council_id: str) -> Optional[CouncilResponse]:
        """获取议会详情"""
        council = await self._load_council(council_id)
        if not council:
            return None
        debate = council.debate_data or {}
        rounds_data = []
        for r in debate.get("rounds", []):
            normalized = dict(r)
            if "exiles_argument" not in normalized and "id_argument" in normalized:
                normalized["exiles_argument"] = normalized.get("id_argument", "")
            if "firefighters_argument" not in normalized and "superego_argument" in normalized:
                normalized["firefighters_argument"] = normalized.get("superego_argument", "")
            rounds_data.append(CouncilRound(**normalized))
        return CouncilResponse(
            council_id=council.id,
            session_id=council.session_id,
            status=council.status,
            current_round=council.rounds,
            total_rounds=debate.get("max_rounds", 5),
            rounds=rounds_data,
            conclusion=council.conclusion,
            started_at=council.started_at,
            completed_at=council.completed_at,
        )

    async def get_active_council(self, session_id: str) -> Optional[CouncilResponse]:
        """获取会话的活跃议会"""
        result = await self.db.execute(
            select(Council).where(Council.session_id == session_id, Council.status == "active")
            .order_by(Council.started_at.desc()).limit(1)
        )
        council = result.scalar_one_or_none()
        if not council:
            return None
        return await self.get_council(council.id)

    async def cancel_council(self, council_id: str) -> bool:
        """取消议会"""
        council = await self._load_council(council_id)
        if not council:
            return False
        council.status = "cancelled"
        council.completed_at = datetime.utcnow()
        await self.db.commit()
        logger.info(f"议会取消: {council_id}")
        return True

    async def get_progress(self, council_id: str) -> Optional[Dict[str, Any]]:
        """获取议会进度（带缓存）"""
        from ..utils.cache import get_or_set

        async def fetch_progress():
            council = await self._load_council(council_id)
            if not council:
                return None
            debate = council.debate_data or {}
            return {
                "council_id": council.id,
                "session_id": council.session_id,
                "status": council.status,
                "progress": f"{council.rounds}/{debate.get('max_rounds', 5)}",
                "current_round": council.rounds,
                "total_rounds": debate.get("max_rounds", 5),
                "topic": debate.get("topic", ""),
                "started_at": council.started_at,
                "elapsed_seconds": (
                    (datetime.utcnow() - council.started_at).total_seconds()
                    if council.status == "active"
                    else ((council.completed_at - council.started_at).total_seconds() if council.completed_at else 0)
                ),
            }

        cache_key = f"council:progress:{council_id}"
        return await get_or_set(cache_key, fetch_progress, ttl=30)  # 缓存30秒

    async def get_history(
        self,
        session_id: str,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取议会历史"""
        try:
            stmt = (
                select(Council)
                .where(Council.session_id == session_id)
                .order_by(Council.started_at.desc())
                .limit(limit)
                .offset(offset)
            )
            result = await self.db.execute(stmt)
            councils = result.scalars().all()

            history = []
            for council in councils:
                debate = council.debate_data or {}
                council_data = {
                    "id": council.id,
                    "session_id": council.session_id,
                    "status": council.status,
                    "topic": debate.get("topic", ""),
                    "rounds": debate.get("rounds", []),
                    "conclusion": council.conclusion,
                    "started_at": council.started_at,
                    "completed_at": council.completed_at,
                }
                history.append(council_data)
            return history
        except Exception as e:
            logger.error(f"获取议会历史失败: {session_id}, 错误: {e}")
            return []

    async def continue_council(
        self,
        council_id: str,
        background_tasks: BackgroundTasks
    ) -> bool:
        """继续执行已暂停的议会"""
        council = await self._load_council(council_id)
        if not council or council.status != "paused":
            return False
        council.status = "active"
        await self.db.commit()
        background_tasks.add_task(self._execute_council, council_id, resume=True)
        logger.info(f"议会继续: {council_id}")
        return True

    async def _execute_council(self, council_id: str, resume: bool = False):
        """执行议会辩论（后台任务）"""
        logger.info(f"开始执行议会辩论: {council_id}, resume={resume}")
        try:
            council = await self._load_council(council_id)
            if not council or council.status != "active":
                return

            debate = council.debate_data or {}
            session_id = council.session_id
            topic = debate.get("topic", "")
            max_rounds = debate.get("max_rounds", 5)
            rounds_list = debate.get("rounds", [])
            start_round = len(rounds_list) if resume else 0

            for round_num in range(start_round, max_rounds):
                # 构建历史（格式: [Exiles]: content [Firefighters]: content）
                utterances = []
                for r in rounds_list:
                    utterances.append(f"[Exiles]: {r['exiles_argument']}")
                    utterances.append(f"[Firefighters]: {r['firefighters_argument']}")
                history_text = "\n".join(utterances)

                exiles_argument = await self.external_apis.generate_council_debate(
                    persona="exiles", topic=topic, round_number=round_num + 1, history_text=history_text
                )
                firefighters_argument = await self.external_apis.generate_council_debate(
                    persona="firefighters", topic=topic, round_number=round_num + 1,
                    history_text=history_text + f"\n[Exiles]: {exiles_argument}"
                )
                counselor_analysis = await self.external_apis.generate_counselor_insight(
                    topic=topic,
                    debate_history=history_text + f"\n[Exiles]: {exiles_argument}\n[Firefighters]: {firefighters_argument}"
                )

                round_data = {
                    "round_number": round_num + 1,
                    "exiles_argument": exiles_argument,
                    "firefighters_argument": firefighters_argument,
                    "counselor_analysis": counselor_analysis,
                }
                rounds_list.append(round_data)

                # 每轮更新 DB
                debate["rounds"] = rounds_list
                council.debate_data = debate
                council.rounds = round_num + 1
                await self.db.commit()
                # 清除进度缓存
                await council_cache.delete(f"council:progress:{council_id}")

                # SSE 推送
                try:
                    await connection_manager.send_event(session_id, {
                        "event_type": "council_update",
                        "data": {
                            "council_id": council_id,
                            "round": round_num + 1,
                            "total_rounds": max_rounds,
                            "exiles_argument": exiles_argument,
                            "firefighters_argument": firefighters_argument,
                            "counselor_analysis": counselor_analysis,
                            "timestamp": datetime.utcnow().isoformat(),
                        }
                    })
                except Exception as e:
                    logger.error(f"发送SSE更新事件失败: {e}")

                logger.info(f"议会轮次完成: {council_id} 第{round_num + 1}轮")
                import asyncio
                await asyncio.sleep(1)

            # 最终结论
            utterances = []
            for r in rounds_list:
                utterances.append(f"[Exiles]: {r['exiles_argument']}")
                utterances.append(f"[Firefighters]: {r['firefighters_argument']}")
                utterances.append(f"[Counselor]: {r['counselor_analysis']}")
            final_history = "\n".join(utterances)

            conclusion = await self.external_apis.generate_counselor_insight(topic=topic, debate_history=final_history)
            council.conclusion = conclusion
            council.status = "completed"
            council.completed_at = datetime.utcnow()
            await self.db.commit()
            # 清除进度缓存
            await council_cache.delete(f"council:progress:{council_id}")

            logger.info(f"议会完成: {council_id}")

            # 发送议会完成事件
            try:
                await connection_manager.send_event(session_id, {
                    "event_type": "council_complete",
                    "data": {
                        "council_id": council_id,
                        "conclusion": conclusion[:200] if conclusion else "",
                        "total_rounds": max_rounds,
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                })
            except Exception as e:
                logger.error(f"发送SSE完成事件失败: {e}")

            # 议会完成后提取核心信念
            try:
                counselor_service = CounselorService(self.external_apis)
                # 使用议会结论作为输入，附加上下文说明这是议会结论
                analysis_input = f"议会结论: {conclusion}"
                history_context = f"议会议题: {topic}\n议会完整记录:\n{final_history}"
                counselor_report = await counselor_service.analyze_trauma(analysis_input, history_context)

                if counselor_report.core_beliefs:
                    # 发送核心信念更新事件
                    await connection_manager.send_event(session_id, {
                        "event_type": "counselor_report",
                        "data": {
                            "core_beliefs": [
                                {"content": b.content, "valence": b.valence, "intensity": b.intensity}
                                for b in counselor_report.core_beliefs
                            ],
                            "trigger_event": counselor_report.trigger_event,
                            "emotional_summary": counselor_report.emotional_summary,
                            "source": "council",  # 标记来源为议会
                            "council_id": council_id,
                        }
                    })
                    logger.info(f"议会后核心信念更新: {council_id}, 信念数量: {len(counselor_report.core_beliefs)}")
                else:
                    logger.warning(f"议会后未提取到核心信念: {council_id}")
            except Exception as e:
                logger.error(f"议会后核心信念提取失败: {council_id}, 错误: {e}")

        except Exception as e:
            logger.error(f"议会执行失败: {council_id}, 错误: {e}")
            try:
                council = await self._load_council(council_id)
                if council:
                    council.status = "failed"
                    council.completed_at = datetime.utcnow()
                    await self.db.commit()
                    # 清除进度缓存
                    await council_cache.delete(f"council:progress:{council_id}")
            except Exception:
                pass


async def example_usage():
    """示例用法"""
    from ..database.database import AsyncSessionLocal
    from fastapi import BackgroundTasks

    async with AsyncSessionLocal() as db:
        service = CouncilService(db)

        # 启动议会
        council = await service.start_council(
            session_id="test_session",
            topic="如何处理工作压力",
            max_rounds=3,
            background_tasks=BackgroundTasks()
        )

        print(f"议会启动: {council.council_id}")
        print(f"状态: {council.status}")
        print(f"话题: {council.current_round}/{council.total_rounds}")


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())