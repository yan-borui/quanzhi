# -*- coding: utf-8 -*-
# Swordsman.py
from core.event_log import emit
from typing import Optional, List

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill


class Swordsman(Character):
    def __init__(self, name: str = "剑客"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        self.invincible_strike_used = set()

    def _initialize_skills(self):
        effortless_slash = Skill("游刃斩", cooldown=1)
        effortless_slash.set_effect(self._effortless_slash_effect)
        self.add_or_replace_skill(effortless_slash)

        whirlwind_slash = Skill("回旋斩", cooldown=1)
        whirlwind_slash.set_effect(self._whirlwind_slash_effect)
        self.add_or_replace_skill(whirlwind_slash)

        lightning_strike = Skill("闪电劈", cooldown=0)
        lightning_strike.set_effect(self._lightning_strike_effect)
        self.add_or_replace_skill(lightning_strike)

        invincible_thrust = Skill("无敌刺", cooldown=0)
        invincible_thrust.set_effect(self._invincible_thrust_effect)
        self.add_or_replace_skill(invincible_thrust)

    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        def validate():
            if skill_name == "闪电劈" and target.get_imprint("剑意") < 3:
                return (
                    "闪电劈需要目标有3层剑意印记，"
                    f"当前只有{target.get_imprint('剑意')}层"
                )
            if skill_name == "无敌刺":
                if id(target) in self.invincible_strike_used:
                    return "无敌刺在同一局中对同一目标只能使用一次！"
                if not target.has_control("lightning_strike"):
                    return "无敌刺需要目标有闪电劈控制效果！"
            return None

        self.execute_skill_action(skill_name, target, validate)

    def describe_skill_action(self, skill_name: str, skill: Skill, battle) -> str:
        if skill_name == "闪电劈":
            has_valid_target = any(
                char.get_imprint("剑意") >= 3
                for char in battle.alive_characters
                if char != self
            )
            if has_valid_target:
                return self.format_skill_action(skill_name, skill)
            return self.format_skill_action(skill_name, skill, "无有效目标")

        if skill_name == "无敌刺":
            valid_targets = [
                char
                for char in battle.alive_characters
                if char != self
                and char.has_control("lightning_strike")
                and id(char) not in self.invincible_strike_used
            ]
            if valid_targets:
                return self.format_skill_action(skill_name, skill)
            return self.format_skill_action(skill_name, skill, "无有效目标")

        return super().describe_skill_action(skill_name, skill, battle)

    def use_whirlwind_on_targets(self, targets: List[Character]):
        skill = self.get_skill("回旋斩")
        if not skill:
            emit(f"{self.name} 没有技能: 回旋斩")
            return False
        if not skill.is_available():
            emit(f"技能 回旋斩 在冷却中 (CD:{skill.get_cooldown()})")
            return False
        if not targets:
            emit(f"回旋斩没有有效目标！")
            return False

        emit(f"{self.name} 使用了 回旋斩！")
        damage = self.apply_attack_buff(6)
        for target in targets:
            target.take_damage(damage)
            target.add_imprint("剑意", 1)

        skill.start_cooldown()
        return True

    def _effortless_slash_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        target.add_imprint("剑意", 1)
        return True

    def _whirlwind_slash_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        # 单体入口仅用于接口兼容，真实逻辑使用 use_whirlwind_on_targets
        return False

    def _lightning_strike_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        if not target:
            return False
        target.add_control("lightning_strike", 1)
        return True

    def _invincible_thrust_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(42))
        self.invincible_strike_used.add(id(target))
        return True

    def on_behavior_change(
        self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            emit(f"{self.name} 持剑向前逼近！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            emit(f"{self.name} 后撤步保持距离！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            emit(f"{self.name} 运功冲破控制束缚！")

    def reset_battle_round(self):
        self.invincible_strike_used.clear()
        emit(f"{self.name} 准备就绪，无敌刺使用记录已重置")


SWORDSMAN_SKILLS_DATA = {
    "游刃斩": {
        "name": "游刃斩",
        "cooldown": 1,
        "damage": 6,
        "effect": "添加剑意印记",
        "range": "任意",
    },
    "回旋斩": {
        "name": "回旋斩",
        "cooldown": 1,
        "damage": 6,
        "effect": "范围伤害，对同一块内所有敌方单位造成伤害并添加剑意印记",
        "range": "近程范围",
        "special": "对同一块内所有非自身角色造成伤害",
    },
    "闪电劈": {
        "name": "闪电劈",
        "cooldown": 0,
        "damage": 0,
        "effect": "施加控制",
        "requirement": "需要目标有3层剑意印记",
    },
    "无敌刺": {
        "name": "无敌刺",
        "cooldown": 0,
        "damage": 42,
        "effect": "高额伤害",
        "requirement": "需要目标有闪电劈控制，且同一局对同一目标只能使用一次",
    },
}

SWORDSMAN_STATS_DATA = {
    "name": "剑客",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "近战输出",
    "description": "擅长连击和控制的高伤害角色",
}
