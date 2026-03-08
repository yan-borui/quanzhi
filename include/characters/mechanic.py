# -*- coding: utf-8 -*-
# mechanic.py - 机械师
"""
机械师角色实现

技能表：
- 机械空投 (CD:2) — 12伤害
- 机械追踪 (CD:1) — 6伤害
- 跳雷 (CD:1) — 6伤害
- 电子眼 (CD:0) — 使"找"无需判定，直接找出隐身目标

关键机制：
- 电子眼可以绕过忍法地心等隐身效果的判定，直接找出目标
- 电子眼对目标使用，调用目标的 be_found_directly 方法
"""

from typing import Optional

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill


class Mechanic(Character):
    def __init__(self, name: str = "机械师"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()

    def _initialize_skills(self):
        airdrop = Skill("机械空投", cooldown=2)
        airdrop.set_effect(self._airdrop_effect)
        self.add_or_replace_skill(airdrop)

        tracking = Skill("机械追踪", cooldown=1)
        tracking.set_effect(self._tracking_effect)
        self.add_or_replace_skill(tracking)

        mine = Skill("跳雷", cooldown=1)
        mine.set_effect(self._mine_effect)
        self.add_or_replace_skill(mine)

        eye = Skill("电子眼", cooldown=0)
        eye.set_effect(self._eye_effect)
        self.add_or_replace_skill(eye)

    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return

        if not skill.is_available():
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return

        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    # --- 技能效果函数 ---

    def _airdrop_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """机械空投：12点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(12))
        return True

    def _tracking_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """机械追踪：6点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def _mine_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """跳雷：6点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def _eye_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """
        电子眼：使"找"无需判定，直接找出隐身目标。
        对目标使用，若目标处于隐身状态则直接找出。
        """
        if not target:
            return False

        if target.stealth <= 0:
            print(f"{target.get_name()} 当前未隐身，无需使用电子眼")
            return False

        # 调用目标的 be_found_directly 方法（如忍者已实现此接口）
        if hasattr(target, "be_found_directly"):
            target.be_found_directly(self)
        else:
            # 通用处理：直接清除隐身
            target.stealth = 0
            print(f"{self.name} 的电子眼直接找出了 {target.get_name()}！")

        return True

    def on_behavior_change(
        self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 操纵机械向前推进！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 启动推进器后撤！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 激活电磁脉冲挣脱束缚！")


MECHANIC_SKILLS_DATA = {
    "机械空投": {
        "name": "机械空投",
        "cooldown": 2,
        "damage": 12,
        "effect": "无",
        "common": True,
    },
    "机械追踪": {
        "name": "机械追踪",
        "cooldown": 1,
        "damage": 6,
        "effect": "无",
    },
    "跳雷": {
        "name": "跳雷",
        "cooldown": 1,
        "damage": 6,
        "effect": "无",
    },
    "电子眼": {
        "name": "电子眼",
        "cooldown": 0,
        "damage": 0,
        "effect": "使'找'无需判定，直接找出隐身目标",
        "special": "绕过判定直接找出",
    },
}

MECHANIC_STATS_DATA = {
    "name": "机械师",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "远程输出/侦察",
    "description": "以机械装置进行远程打击和侦察的角色，电子眼可直接找出隐身目标",
}
