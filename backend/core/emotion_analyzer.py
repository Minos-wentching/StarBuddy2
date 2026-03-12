"""
情绪分析器

分析文本情绪强度，支持外部API调用和模拟模式
"""

import logging
import random
import re
from typing import Dict, Any, Optional
import httpx

from ..api_config import config
from ..models.schemas import EmotionAnalysis

logger = logging.getLogger(__name__)


class EmotionAnalyzer:
    """情绪分析器"""

    def __init__(self):
        self.use_external_api = bool(config.DASHSCOPE_EMOTION_API_KEY)
        self.client = httpx.AsyncClient(timeout=30.0) if self.use_external_api else None

        # 情感关键词库（简化版）
        self.emotion_keywords = {
            "happy": ["开心", "快乐", "高兴", "喜悦", "幸福", "愉快", "兴奋"],
            "sad": ["悲伤", "难过", "伤心", "沮丧", "失望", "痛苦", "哭泣"],
            "angry": ["生气", "愤怒", "恼火", "气愤", "烦躁", "暴怒", "怒火"],
            "anxious": ["焦虑", "紧张", "担心", "不安", "恐惧", "害怕", "恐慌"],
            "calm": ["平静", "安宁", "放松", "镇定", "平和", "舒缓", "宁静"]
        }

        # 强度修饰词
        self.intensity_modifiers = {
            "high": ["非常", "极其", "特别", "十分", "超级", "极度", "异常"],
            "medium": ["比较", "相当", "挺", "颇为", "有些", "有点"],
            "low": ["稍微", "略微", "稍稍", "一点", "些许"]
        }

    async def analyze(self, text: str) -> float:
        """分析文本情绪强度"""
        try:
            if self.use_external_api and config.DASHSCOPE_EMOTION_API_KEY:
                # 使用外部API
                return await self._analyze_with_external_api(text)
            else:
                # 使用模拟分析
                return self._analyze_with_keywords(text)

        except Exception as e:
            logger.error(f"情绪分析失败: {e}")
            # 返回中性情绪作为降级
            return 0.5

    async def analyze_detailed(self, text: str) -> EmotionAnalysis:
        """详细情绪分析"""
        intensity = await self.analyze(text)

        # 识别主导情绪
        dominant_emotion = self._detect_dominant_emotion(text)

        # 计算情绪成分
        components = self._calculate_emotion_components(text)

        return EmotionAnalysis(
            intensity=intensity,
            dominant_emotion=dominant_emotion,
            confidence=0.8,  # 置信度
            components=components
        )

    async def _analyze_with_external_api(self, text: str) -> float:
        """使用DashScope API分析情绪"""
        try:
            # 构建请求
            request_data = {
                "model": config.DASHSCOPE_EMOTION_MODEL,
                "input": {
                    "messages": [
                        {
                            "role": "system",
                            "content": "你是一个情感分析专家。分析以下文本的情绪强度，返回0到1之间的数值，其中0表示非常消极/平静，1表示非常积极/激动。只返回数字，不要解释。"
                        },
                        {
                            "role": "user",
                            "content": text
                        }
                    ]
                },
                "parameters": {
                    "temperature": 0.1,
                    "max_tokens": 10
                }
            }

            # 发送请求
            response = await self.client.post(
                config.DASHSCOPE_EMOTION_URL,
                headers=config.dashscope_emotion_headers,
                json=request_data
            )

            response.raise_for_status()
            result = response.json()

            # 解析响应
            if "output" in result and "text" in result["output"]:
                response_text = result["output"]["text"].strip()
                # 提取数字
                numbers = re.findall(r"[-+]?\d*\.\d+|\d+", response_text)
                if numbers:
                    intensity = float(numbers[0])
                    # 确保在0-1范围内
                    intensity = max(0.0, min(1.0, intensity))
                    logger.debug(f"API情绪分析结果: {text[:50]}... -> {intensity}")
                    return intensity

            # 如果无法解析，使用降级方案
            logger.warning(f"无法解析API响应: {result}")
            return self._analyze_with_keywords(text)

        except httpx.HTTPError as e:
            logger.error(f"API请求失败: {e}")
            # 降级到关键词分析
            return self._analyze_with_keywords(text)
        except Exception as e:
            logger.error(f"API分析异常: {e}")
            return self._analyze_with_keywords(text)

    def _analyze_with_keywords(self, text: str) -> float:
        """使用关键词分析情绪强度"""
        text_lower = text.lower()

        # 初始化情绪分数
        emotion_scores = {emotion: 0.0 for emotion in self.emotion_keywords.keys()}

        # 检测关键词
        for emotion, keywords in self.emotion_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    emotion_scores[emotion] += 1.0

        # 检测强度修饰词
        intensity_multiplier = 1.0
        for level, modifiers in self.intensity_modifiers.items():
            for modifier in modifiers:
                if modifier in text_lower:
                    if level == "high":
                        intensity_multiplier = 1.5
                    elif level == "medium":
                        intensity_multiplier = 1.0
                    elif level == "low":
                        intensity_multiplier = 0.5
                    break

        # 计算总体强度
        total_score = sum(emotion_scores.values())

        if total_score == 0:
            # 没有检测到情感词，返回中性
            base_intensity = 0.5
        else:
            # 根据情感类型调整基准强度
            if emotion_scores["happy"] > 0:
                base_intensity = 0.7
            elif emotion_scores["angry"] > 0 or emotion_scores["anxious"] > 0:
                base_intensity = 0.8
            elif emotion_scores["sad"] > 0:
                base_intensity = 0.6
            elif emotion_scores["calm"] > 0:
                base_intensity = 0.3
            else:
                base_intensity = 0.5

            # 根据检测到的情感词数量调整
            detection_ratio = min(1.0, total_score / 5.0)
            intensity_variation = detection_ratio * 0.3  # 最多±0.3的变化

            if base_intensity > 0.5:
                base_intensity += intensity_variation
            else:
                base_intensity -= intensity_variation

        # 应用强度修饰词
        final_intensity = base_intensity * intensity_multiplier

        # 确保在0-1范围内
        final_intensity = max(0.0, min(1.0, final_intensity))

        logger.debug(f"关键词情绪分析: {text[:50]}... -> {final_intensity:.2f}")
        return final_intensity

    def _detect_dominant_emotion(self, text: str) -> Optional[str]:
        """检测主导情绪"""
        text_lower = text.lower()
        emotion_counts = {}

        for emotion, keywords in self.emotion_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            if count > 0:
                emotion_counts[emotion] = count

        if not emotion_counts:
            return None

        # 返回出现次数最多的情绪
        return max(emotion_counts.items(), key=lambda x: x[1])[0]

    def _calculate_emotion_components(self, text: str) -> Dict[str, float]:
        """计算情绪成分"""
        text_lower = text.lower()
        components = {}

        for emotion, keywords in self.emotion_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            total_keywords = len(keywords)

            if total_keywords > 0:
                components[emotion] = count / total_keywords

        # 归一化
        total = sum(components.values())
        if total > 0:
            components = {k: v / total for k, v in components.items()}

        return components

    async def close(self):
        """关闭HTTP客户端"""
        if self.client:
            await self.client.aclose()


async def example_usage():
    """示例用法"""
    analyzer = EmotionAnalyzer()

    test_texts = [
        "我今天非常开心，阳光明媚！",
        "我感到有点焦虑，担心明天的事情。",
        "这让我非常愤怒，简直无法忍受！",
        "平静的湖面让我心情放松。",
        "普通的一天，没什么特别的感觉。"
    ]

    print("=== 情绪分析测试 ===")
    for text in test_texts:
        intensity = await analyzer.analyze(text)
        analysis = await analyzer.analyze_detailed(text)

        print(f"\n文本: {text}")
        print(f"强度: {intensity:.2f}")
        print(f"主导情绪: {analysis.dominant_emotion}")
        print(f"情绪成分: {analysis.components}")

    await analyzer.close()


if __name__ == "__main__":
    import asyncio
    asyncio.run(example_usage())