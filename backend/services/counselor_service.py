"""
咨询师服务 (Counselor Service)

负责深度心理分析、核心信念提取和情绪强度评估。
参考 Multiego 的 CounselorAgent 实现，包含 JSON 修复功能。
"""

import logging
import json
import re
import types
from typing import Dict, Any, Optional, List
from .external_apis import ExternalAPIService
from ..models.schemas import CoreBelief, CounselorReport
from .prompts import COUNSELOR_SYSTEM_PROMPT, ONBOARDING_PROFILE_PARSE_PROMPT

logger = logging.getLogger(__name__)


class CounselorService:
    def __init__(self, external_api: ExternalAPIService):
        self.external_api = external_api

    async def analyze_trauma(self, user_input: str, history_text: str = "") -> CounselorReport:
        """分析心理动态并生成报告"""

        analysis_request = (
            "请深入分析用户的输入，识别其背后的核心信念、触发事件和情绪总结。\n"
            "必须以严格的 JSON 格式返回，不要包含任何多余的文字说明。\n\n"
            f"用户输入: {user_input}\n"
            f"历史背景: {history_text}"
        )

        try:
            raw_output = await self.external_api.generate_dialogue_response(
                persona="counselor",
                message=analysis_request,
                system_prompt=COUNSELOR_SYSTEM_PROMPT
            )

            logger.debug(f"Counselor raw output: {raw_output}")

            # 使用多策略解析
            report = await self._parse_report(raw_output)

            # 如果解析失败，重试一次
            if not report.core_beliefs and not report.trigger_event and not report.emotional_summary:
                raw_output = await self.external_api.generate_dialogue_response(
                    persona="counselor",
                    message="上一次返回格式错误。请严格只返回 JSON 对象，不要有 Markdown 代码块标记。内容必须包含 core_beliefs, trigger_event, emotional_summary。",
                    system_prompt=COUNSELOR_SYSTEM_PROMPT
                )
                report = await self._parse_report(raw_output)

            if not report.core_beliefs and not report.trigger_event and not report.emotional_summary:
                return self._fallback_report(user_input)

            return report

        except Exception as e:
            logger.error(f"Counselor analysis failed: {e}")
            return self._fallback_report(user_input)

    async def _parse_report(self, raw: str) -> CounselorReport:
        """解析 LLM 返回的 JSON 为 CounselorReport，多层兜底确保不崩溃 (移植自 Multiego)"""
        raw_text = self._coerce_raw_text(raw)
        if not raw_text or not raw_text.strip():
            logger.warning("Counselor returned empty output")
            return CounselorReport(raw_analysis="", emotional_summary="")

        data = self._extract_json(raw_text)

        # 本地解析全部失败 → 调用 DashScope API 修复
        if data is None:
            logger.info("Local JSON parse failed, attempting DashScope repair")
            data = await self._repair_json_via_api(raw_text)

        if not isinstance(data, dict):
            logger.warning("All JSON parse attempts failed, using fallback report")
            return CounselorReport(
                raw_analysis=raw_text,
                emotional_summary=raw_text[:200],
            )

        return self._build_report(data, raw_text)

    def _extract_json(self, text: str) -> Optional[Dict[str, Any]]:
        """多策略本地 JSON 提取 (移植自 Multiego)"""
        if not text:
            return None

        cleaned = text.strip()

        # 策略1: ```json ... ``` fence block
        for pattern in [r"```json\s*([\s\S]*?)\s*```", r"```\s*([\s\S]*?)\s*```"]:
            fence = re.search(pattern, cleaned, re.IGNORECASE)
            if fence:
                result = self._try_parse_json(fence.group(1).strip())
                if result is not None:
                    return result

        # 策略2: 匹配最外层大括号
        brace_start = cleaned.find("{")
        brace_end = cleaned.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            result = self._try_parse_json(cleaned[brace_start:brace_end + 1])
            if result is not None:
                return result

        # 策略3: 逐行清理常见破坏 JSON 的字符后重试
        sanitized = cleaned
        for pattern in [
            r"```json\s*", r"```\s*",
            r"^[^{\[]*(?=\{)",
        ]:
            sanitized = re.sub(pattern, "", sanitized, flags=re.MULTILINE)
        sanitized = sanitized.rstrip("`").strip()
        brace_start = sanitized.find("{")
        brace_end = sanitized.rfind("}")
        if brace_start != -1 and brace_end > brace_start:
            result = self._try_parse_json(sanitized[brace_start:brace_end + 1])
            if result is not None:
                return result

        return None

    def _try_parse_json(self, text: str) -> Optional[Dict[str, Any]]:
        """尝试解析 JSON 字符串，自动修复常见问题 (移植自 Multiego)"""
        if not text:
            return None
        for attempt_text in [text, self._fix_common_json_issues(text)]:
            try:
                obj = json.loads(attempt_text)
                if isinstance(obj, dict):
                    return obj
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    @staticmethod
    def _fix_common_json_issues(text: str) -> str:
        """修复常见的 JSON 格式问题 (移植自 Multiego)"""
        fixed = text
        # 移除行尾注释 // ...
        fixed = re.sub(r'//[^\n]*', '', fixed)
        # 移除尾部多余逗号 ,] 或 ,}
        fixed = re.sub(r',\s*([}\]])', r'\1', fixed)
        # 将单引号替换为双引号
        fixed = re.sub(r"(?<![\\])'", '"', fixed)
        # 修复未闭合的括号
        open_braces = fixed.count("{") - fixed.count("}")
        open_brackets = fixed.count("[") - fixed.count("]")
        if open_braces > 0:
            fixed += "}" * open_braces
        if open_brackets > 0:
            fixed += "]" * open_brackets
        return fixed

    async def _repair_json_via_api(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """调用 DashScope API 将损坏的文本修复为标准 JSON (移植自 Multiego)"""
        repair_prompt = (
            "你是一个 JSON 修复专家。下面的文本本应是一个 JSON 对象，但格式可能有问题"
            "（多余文字、截断、缺少引号/括号、注释等）。\n"
            "请提取并修复为合法 JSON，必须包含以下字段（缺失则用空值补全）：\n"
            '- core_beliefs: 数组，每项含 content(str), valence(float), intensity(float), origin_event(str)\n'
            '- trigger_event: 字符串\n'
            '- emotional_summary: 字符串\n\n'
            "仅输出修复后的纯 JSON，不要输出任何其他内容，不要用 markdown 包裹。\n\n"
            f"待修复文本：\n{raw_text[:3000]}"
        )
        try:
            result = await self.external_api.generate_dialogue_response(
                persona="counselor",
                message=repair_prompt,
                system_prompt="你是JSON修复助手。只输出合法JSON，不要输出任何其他内容。"
            )
            result = self._coerce_raw_text(result)
            parsed = self._extract_json(result)
            if parsed is not None:
                logger.info("DashScope JSON repair succeeded")
                return parsed
            logger.warning("DashScope repair returned unparseable result")
        except Exception as e:
            logger.warning("DashScope JSON repair failed: %s", e)
        return None

    def _build_report(self, data: Dict[str, Any], raw_text: str) -> CounselorReport:
        """从解析好的 dict 构建 CounselorReport"""
        beliefs = []
        for b in data.get("core_beliefs", []):
            if not isinstance(b, dict):
                continue
            try:
                beliefs.append(CoreBelief(
                    belief_id=str(b.get("belief_id", "")),
                    content=str(b.get("content", "")),
                    valence=float(b.get("valence", 0)),
                    intensity=float(b.get("intensity", 5)),
                    origin_event=str(b.get("origin_event", ""))
                ))
            except (TypeError, ValueError):
                continue

        return CounselorReport(
            core_beliefs=beliefs,
            intensity_scores={b.content: b.intensity for b in beliefs},
            trigger_event=str(data.get("trigger_event", "")),
            emotional_summary=str(data.get("emotional_summary", "")),
            raw_analysis=raw_text
        )

    def _coerce_raw_text(self, raw) -> str:
        """将各种类型的输出转换为字符串 (移植自 Multiego)"""
        if raw is None:
            return ""
        if isinstance(raw, str):
            return raw
        if isinstance(raw, types.GeneratorType):
            return "".join(raw)
        return str(raw)

    def _fallback_report(self, user_input: str) -> CounselorReport:
        """当 API 调用或 JSON 解析失败时，返回兜底报告"""
        return CounselorReport(
            core_beliefs=[],
            intensity_scores={},
            trigger_event="",
            emotional_summary=f"无法完成深度分析，用户原始输入: {user_input[:200]}",
            raw_analysis=None
        )

    async def extract_user_facts(self, user_input: str, existing_facts: List[str]) -> List[str]:
        """提取用户事实 (参照 Multiego)"""
        facts_text = "\n".join([f"- {f}" for f in existing_facts]) if existing_facts else "无"

        prompt = (
            "从以下用户输入中，提取明确提到的个人基本信息。\n"
            "仅提取客观事实，不要推测或编造。\n"
            "包括但不限于：性别、年龄、所在城市、工作/职业、婚姻状况、家庭成员、重要人生经历等。\n\n"
            f"用户输入：\n{user_input}\n\n"
            f"已知信息：\n{facts_text}\n\n"
            "请输出JSON格式（仅包含新发现的、不与已知信息重复的事实）：\n"
            "{\"new_facts\": [\"用户性别为男\", \"用户在深圳工作\"]}\n\n"
            "如果没有新的个人信息，返回：{\"new_facts\": []}"
        )

        try:
            raw = await self.external_api.generate_dialogue_response(
                persona="counselor",
                message=prompt,
                system_prompt="你是一个信息提取助手。请只输出 JSON。"
            )
            data = self._extract_json(raw)
            return data.get("new_facts", []) if data else []
        except Exception as e:
            logger.warning(f"Failed to extract user facts: {e}")
            return []

    async def parse_onboarding_answers(self, answers: Dict[str, str]) -> Dict[str, Any]:
        """解析首次登录问卷，生成 Exiles / Firefighters 提示词和核心画像"""
        joined_answers = (
            f"Q1: {answers.get('question_1', '')}\n"
            f"Q2: {answers.get('question_2', '')}\n"
            f"Q3: {answers.get('question_3', '')}\n"
            f"Q4: {answers.get('question_4', '')}"
        )

        raw = await self.external_api.generate_dialogue_response(
            persona="counselor",
            message=f"用户首次登录问卷：\n{joined_answers}",
            system_prompt=ONBOARDING_PROFILE_PARSE_PROMPT
        )

        data = self._extract_json(raw) or {}
        portraits = data.get("persona_portraits", {})
        if not isinstance(portraits, dict):
            portraits = {}

        exiles_portrait = str(portraits.get("exiles", "")).strip()[:180]
        firefighters_portrait = str(portraits.get("firefighters", "")).strip()[:180]

        return {
            "exiles_system_prompt": str(data.get("exiles_system_prompt", "")).strip(),
            "firefighters_system_prompt": str(data.get("firefighters_system_prompt", "")).strip(),
            "trauma_hypothesis": str(data.get("trauma_hypothesis", "")).strip(),
            "user_core_info": data.get("user_core_info", []) if isinstance(data.get("user_core_info", []), list) else [],
            "core_beliefs": data.get("core_beliefs", []) if isinstance(data.get("core_beliefs", []), list) else [],
            "profile_digest": str(data.get("profile_digest", "")).strip()[:240],
            "persona_portraits": {
                "exiles": exiles_portrait,
                "firefighters": firefighters_portrait,
            }
        }
