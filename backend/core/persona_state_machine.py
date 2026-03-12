"""
人格状态机

根据情绪强度管理人格切换和状态转移
"""

import logging
from collections import deque
from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..api_config import APIConfig

logger = logging.getLogger(__name__)


@dataclass
class PersonaState:
    """人格状态"""
    current_persona: str
    persona_changed: bool = False
    trigger_council: bool = False
    emotion_intensity: float = 0.0
    switch_reason: Optional[str] = None


class PersonaStateMachine:
    """人格状态机 (Refactored to match Multiego logic)"""

    def __init__(self, config: APIConfig):
        self.config = config
        self.current_persona = "manager"
        self.emotion_intensity = 0.0
        self.emotion_history = deque(maxlen=config.EMOTION_HISTORY_SIZE)
        self.transition_count = 0
        self.turns_since_switch = 0  # 切换后持续的回合数

        # 人格配置
        self.personas = {
            "manager": {
                "name": "安全岛",
                "description": "稳定、可预测的交流基地，提供安全感"
            },
            "exiles": {
                "name": "感知精灵",
                "description": "感官敏感的自我，感知情绪与感官过载"
            },
            "firefighters": {
                "name": "规则守卫",
                "description": "守护秩序与规律，在变化中寻找确定性"
            }
        }

    def update(self, raw_intensity: float) -> PersonaState:
        """更新情绪强度并根据 Multiego 逻辑进行衰减和切换"""
        
        # 1. 强度衰减逻辑 (参照 Multiego HealingOrchestrator._compute_intensity)
        intensity = raw_intensity
        if self.current_persona != "manager" and self.turns_since_switch > 0:
            decay_rate = getattr(self.config, "EMOTION_DECAY_RATE", 0.05)
            decay_multiplier = max(0.0, 1.0 - self.turns_since_switch * decay_rate)
            intensity = max(0.0, min(1.0, raw_intensity * decay_multiplier))
        
        self.emotion_intensity = intensity
        self.emotion_history.append(intensity)
        
        old_persona = self.current_persona
        persona_changed = False
        trigger_council = False
        switch_reason = None

        # 2. 切换逻辑
        # 如果当前是 manager，检查是否超过阈值进入子人格
        if self.current_persona == "manager":
            if intensity > self.config.INTENSITY_SWITCH_THRESHOLD:
                # 基于情绪波动性区分 Exiles 和 Firefighters
                # 高波动 → Exiles（原始情绪爆发），低波动 → Firefighters（持续保护压力）
                if self._is_exiles_dominant(intensity):
                    self.current_persona = "exiles"
                    switch_reason = self._get_switch_reason(old_persona, "exiles", intensity)
                elif self._is_firefighters_dominant(intensity):
                    self.current_persona = "firefighters"
                    switch_reason = self._get_switch_reason(old_persona, "firefighters", intensity)
                else:
                    # 波动性不明确时默认 Exiles（情绪紧迫性更高）
                    self.current_persona = "exiles"
                    switch_reason = f"情绪强度({intensity:.2f})超过阈值，默认进入 Exiles"
                persona_changed = True
                trigger_council = self._should_trigger_council(old_persona, self.current_persona)
        
        # 如果当前是子人格，检查是否低于返回阈值
        else:
            self.turns_since_switch += 1
            if intensity <= self.config.CALM_THRESHOLD:
                self.current_persona = "manager"
                persona_changed = True
                self.turns_since_switch = 0
                switch_reason = f"情绪趋于平静({intensity:.2f})"

        if persona_changed:
            self.transition_count += 1
            logger.info(f"Persona Switch: {old_persona} -> {self.current_persona} (Intensity: {intensity:.2f})")

        return PersonaState(
            current_persona=self.current_persona,
            persona_changed=persona_changed,
            trigger_council=trigger_council,
            emotion_intensity=intensity,
            switch_reason=switch_reason
        )

    def _is_exiles_dominant(self, intensity: float) -> bool:
        """判断是否Exiles主导"""
        # 简化逻辑：情绪强度高且近期情绪波动大
        if len(self.emotion_history) < 3:
            return intensity > 0.8

        recent_changes = [
            abs(self.emotion_history[i] - self.emotion_history[i-1])
            for i in range(1, min(4, len(self.emotion_history)))
        ]
        avg_change = sum(recent_changes) / len(recent_changes)

        return intensity > 0.7 and avg_change > 0.2

    def _is_firefighters_dominant(self, intensity: float) -> bool:
        """判断是否Firefighters主导"""
        # 简化逻辑：情绪强度高但相对稳定
        if len(self.emotion_history) < 3:
            return intensity > 0.7

        recent_changes = [
            abs(self.emotion_history[i] - self.emotion_history[i-1])
            for i in range(1, min(4, len(self.emotion_history)))
        ]
        avg_change = sum(recent_changes) / len(recent_changes)

        return intensity > 0.7 and avg_change < 0.1

    def _is_council_triggered(self, intensity: float) -> bool:
        """判断是否触发议会"""
        # 当 Exiles 和 Firefighters 之间可能发生冲突时触发议会
        # 简化逻辑：情绪强度高且近期在 Exiles/Firefighters 阈值之间波动
        if len(self.emotion_history) < 3:
            return False

        # 检查近期是否在阈值附近波动
        near_threshold = [
            abs(val - self.config.EXILES_THRESHOLD) < 0.1 or
            abs(val - self.config.FIREFIGHTERS_THRESHOLD) < 0.1
            for val in list(self.emotion_history)[-3:]
        ]

        return sum(near_threshold) >= 2 and intensity > self.config.CALM_THRESHOLD

    def _should_trigger_council(self, old_persona: str, new_persona: str) -> bool:
        """判断是否需要触发议会"""
        # 当在 Exiles 和 Firefighters 之间切换时触发议会，或者从管理者进入子人格时触发
        council_pairs = {
            ("manager", "exiles"), ("manager", "firefighters"),
            ("exiles", "firefighters"), ("firefighters", "exiles")
        }
        return (old_persona, new_persona) in council_pairs

    def _get_switch_reason(self, old_persona: str, new_persona: str, intensity: float) -> str:
        """获取切换原因描述"""
        reasons = {
            ("manager", "exiles"): f"情绪强度({intensity:.2f})超过Exiles阈值({self.config.EXILES_THRESHOLD})",
            ("manager", "firefighters"): f"情绪强度({intensity:.2f})超过Firefighters阈值({self.config.FIREFIGHTERS_THRESHOLD})",
            ("exiles", "manager"): f"情绪强度({intensity:.2f})低于平静阈值({self.config.CALM_THRESHOLD})",
            ("firefighters", "manager"): f"情绪强度({intensity:.2f})低于平静阈值({self.config.CALM_THRESHOLD})",
            ("exiles", "firefighters"): "检测到 Exiles-Firefighters 冲突，触发内心议会",
            ("firefighters", "exiles"): "检测到 Firefighters-Exiles 冲突，触发内心议会",
        }

        return reasons.get((old_persona, new_persona), "未知原因")

    def get_state(self) -> Dict[str, Any]:
        """获取当前状态"""
        return {
            "current_persona": self.current_persona,
            "persona_info": self.personas.get(self.current_persona, {}),
            "emotion_intensity": self.emotion_intensity,
            "emotion_history": list(self.emotion_history),
            "transition_count": self.transition_count,
            "config": {
                "exiles_threshold": self.config.EXILES_THRESHOLD,
                "firefighters_threshold": self.config.FIREFIGHTERS_THRESHOLD,
                "id_threshold": getattr(self.config, "LEGACY_ID_THRESHOLD", None),
                "superego_threshold": getattr(self.config, "LEGACY_SUPEREGO_THRESHOLD", None),
                "calm_threshold": self.config.CALM_THRESHOLD,
                "council_trigger_ratio": self.config.COUNCIL_TRIGGER_RATIO
            }
        }

    def reset(self):
        """重置状态机"""
        self.current_persona = "manager"
        self.emotion_intensity = 0.0
        self.emotion_history.clear()
        self.transition_count = 0
        self.turns_since_switch = 0
        logger.info("状态机已重置")

    def to_dict(self) -> Dict[str, Any]:
        """序列化状态机为字典（用于 DB 持久化）"""
        return {
            "current_persona": self.current_persona,
            "emotion_intensity": self.emotion_intensity,
            "emotion_history": list(self.emotion_history),
            "transition_count": self.transition_count,
            "turns_since_switch": self.turns_since_switch,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any], config: 'APIConfig') -> 'PersonaStateMachine':
        """从字典恢复状态机"""
        sm = cls(config)
        sm.current_persona = data.get("current_persona", "manager")
        sm.emotion_intensity = data.get("emotion_intensity", 0.0)
        sm.turns_since_switch = data.get("turns_since_switch", 0)
        sm.transition_count = data.get("transition_count", 0)
        for val in data.get("emotion_history", []):
            sm.emotion_history.append(val)
        return sm


def example_usage():
    """示例用法"""
    from ..api_config import config

    # 创建状态机
    state_machine = PersonaStateMachine(config)

    # 模拟情绪变化
    test_intensities = [0.1, 0.3, 0.5, 0.8, 0.9, 0.6, 0.2, 0.7, 0.75, 0.4]

    print("=== 人格状态机测试 ===")
    for i, intensity in enumerate(test_intensities):
        state = state_machine.update(intensity)
        print(f"轮次 {i+1}: 强度={intensity:.2f}, "
              f"人格={state.current_persona}, "
              f"切换={state.persona_changed}, "
              f"议会={state.trigger_council}")

    print("\n=== 最终状态 ===")
    final_state = state_machine.get_state()
    print(f"当前人格: {final_state['current_persona']}")
    print(f"情绪强度: {final_state['emotion_intensity']:.2f}")
    print(f"切换次数: {final_state['transition_count']}")


if __name__ == "__main__":
    example_usage()
