"""
Manager Service —— 中枢调度器 (移植自 Multiego agents/manager.py)

与用户直接对话，决定激活哪个次人格，主导议会流程。
"""
from __future__ import annotations

import json
import logging
import re
from typing import Optional, List, Dict, Any

from .external_apis import ExternalAPIService
from .prompts import MANAGER_SYSTEM_PROMPT, MANAGER_CHAT_PROMPT, MANAGER_DECISION_PROMPT
from ..models.schemas import (
    AgentRole,
    ManagerDecision,
    CounselorReport,
    SessionPhase,
)

logger = logging.getLogger(__name__)


class ManagerService:
    """中枢 Manager —— Self 角色 (移植自 Multiego ManagerAgent)"""

    def __init__(self, external_api: ExternalAPIService):
        self.external_api = external_api

    # ──────── 与用户对话 ────────

    async def chat(
        self,
        user_input: str,
        history: List[Dict[str, str]] | None = None,
        user_background: str = "",
        active_agent: str = "manager",
    ) -> str:
        """
        普通对话模式——倾听用户、回应情感。(移植自 Multiego ManagerAgent.chat)
        即使次人格活跃，Manager 也是唯一的对话者。
        使用专用的对话 prompt，不含任何 JSON 指令。
        """
        chat_system = (
            "你是用户的安全岛，一个稳定、温暖、可预测的陪伴者。\n"
            "\n对话原则：\n"
            "- 你只是在和用户聊天，用自然语言回复。\n"
            "- 绝对禁止输出 JSON、代码块、格式化数据。\n"
            "- 语言简洁清晰，不用模糊或抽象的表达。\n"
            "- 当用户表达不适或困惑时，先确认感受，再温和引导。\n"
            "- 用语简短温暖，不超过25字。\n"
            "- 绝不能透露你是一个系统或AI。\n"
            "- 用具体的、可感知的语言和用户交流。\n"
            "示例1：用户：你是谁？回答：我是你的安全岛。不管外面多吵，这里都很安静。\n"
            "示例2：用户：今天学校好吵。回答：嗯，吵的时候确实不舒服。你现在感觉好一点了吗？\n"
        )
        system_prompt = chat_system + user_background

        return await self.external_api.generate_dialogue_response(
            persona="manager",
            message=user_input,
            history=history,
            system_prompt=system_prompt
        )

    # ──────── 调度决策 (核心方法，移植自 Multiego ManagerAgent.decide) ────────

    async def decide(
        self,
        counselor_report: Optional[CounselorReport],
        chat_history: List[Dict[str, str]] | None = None,
    ) -> ManagerDecision:
        """
        根据 Counselor 分析报告做出调度决策：(移植自 Multiego ManagerAgent.decide)
        激活 Exiles 还是 Firefighters？是否需要存档？
        生成 events 和 character_profile。
        """
        if counselor_report is None:
            return ManagerDecision(
                target_agent=AgentRole.EXILES,
                reasoning="No analysis available, defaulting to Exiles for emotional support.",
            )

        # 构建决策 prompt (完全照抄 Multiego)
        decision_prompt = (
            "现在请你做出调度决策。以下是 Counselor 的分析报告：\n\n"
            f"核心信念：\n"
        )
        for b in counselor_report.core_beliefs:
            decision_prompt += f"  - {b.content} (强度: {b.intensity}, 极性: {b.valence})\n"
        decision_prompt += (
            f"\n诱发事件：{counselor_report.trigger_event}\n"
            f"情感概要：{counselor_report.emotional_summary}\n\n"
            "请输出你的调度决策。给出发生人格转换时的事件内容，并为该次人格撰写一份详细的人设包括年龄，身份，性格，爱好（如喜欢吃糖果、害怕黑暗等）\n"
            'json格式如下:\n{"target_agent": "exiles"或"firefighters", "events":"原人格打碎了家里的碗", "character_profile":"五岁，是原人格的哥哥，胆大却有正义感，爱吃糖果，害怕黑暗"}\n'
        )

        extra_system = MANAGER_SYSTEM_PROMPT + "\n\n【当前模式：调度决策模式。请以 JSON 格式输出。】"

        raw = await self.external_api.generate_dialogue_response(
            persona="manager",
            message=decision_prompt,
            history=chat_history[-4:] if chat_history else None,
            system_prompt=extra_system
        )

        logger.debug("Manager decision raw: %s", raw)
        return self._parse_decision(raw)

    # ──────── 解析 (移植自 Multiego ManagerAgent._parse_decision) ────────

    def _parse_decision(self, raw: str) -> ManagerDecision:
        """解析 LLM 返回的决策 JSON (移植自 Multiego)"""
        try:
            json_match = re.search(r'\{[\s\S]*\}', raw)
            if json_match:
                data = json.loads(json_match.group())
            else:
                data = json.loads(raw)

            target_str = data.get("target_agent", "exiles").lower()
            target = AgentRole.EXILES if "exiles" in target_str else AgentRole.FIREFIGHTERS
            events = data.get("events", "")
            character_profile = data.get("character_profile", data.get("character", ""))

            return ManagerDecision(
                target_agent=target,
                reasoning=data.get("reasoning", ""),
                council_topic=data.get("council_topic", ""),
                events=events,
                character_profile=character_profile,
                should_save_block=data.get("should_save_block", False),
            )
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning("Failed to parse manager decision: %s", e)
            return ManagerDecision(
                target_agent=AgentRole.EXILES,
                reasoning=f"Parse failed, defaulting. Raw: {raw[:100]}",
            )

    # ──────── 构建 persona_hint (用于日记写作) ────────

    def build_persona_hint(self, decision: ManagerDecision) -> str:
        """
        从 ManagerDecision 构建 persona_hint，注入到日记 prompt 中。
        (移植自 Multiego 的日记写作逻辑)
        """
        hint_parts = []

        if decision.events:
            hint_parts.append(f"【触发事件】\n{decision.events}")

        if decision.character_profile:
            hint_parts.append(f"【人格设定】\n{decision.character_profile}")

        return "\n\n".join(hint_parts)
