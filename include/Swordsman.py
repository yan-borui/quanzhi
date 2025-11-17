# -*- coding: utf-8 -*-
# Swordsman.py
from typing import Optional

from Behavior import BehaviorType
from Character import Character
from Skill import Skill


class Swordsman(Character):
    def __init__(self, name: str = "剑客"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        self.invincible_strike_used = set()  # 记录本局对哪些目标使用过无敌刺

    def _initialize_skills(self):
        """初始化剑客的技能"""
        # 游刃斩
        effortless_slash = Skill("游刃斩", cooldown=2)
        effortless_slash.set_effect(self._effortless_slash_effect)
        self.add_or_replace_skill(effortless_slash)

        # 回旋斩
        whirlwind_slash = Skill("回旋斩", cooldown=2)
        whirlwind_slash.set_effect(self._whirlwind_slash_effect)
        self.add_or_replace_skill(whirlwind_slash)

        # 闪电劈
        lightning_strike = Skill("闪电劈", cooldown=1)
        lightning_strike.set_effect(self._lightning_strike_effect)
        self.add_or_replace_skill(lightning_strike)

        # 无敌刺
        invincible_thrust = Skill("无敌刺", cooldown=1)
        invincible_thrust.set_effect(self._invincible_thrust_effect)
        self.add_or_replace_skill(invincible_thrust)

    def use_skill(self, skill_name: str):
        """使用技能（默认目标为自己）"""
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        """对目标使用技能"""
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return

        if not skill.is_available():
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return

        # 特殊技能条件检查
        if skill_name == "回旋斩" and not self.is_nearby(target):
            print(f"回旋斩只能攻击附近的目标！{target.name} 不在附近")
            return

        if skill_name == "闪电劈" and target.get_imprint("剑意") < 3:
            print(f"闪电劈需要目标有3层剑意印记，当前只有{target.get_imprint('剑意')}层")
            return

        if skill_name == "无敌刺":
            target_id = id(target)
            if target_id in self.invincible_strike_used:
                print(f"无敌刺在同一局中对同一目标只能使用一次！")
                return
            if not target.has_control("lightning_strike"):
                print(f"无敌刺需要目标有闪电劈控制效果！")
                return

        # 执行技能
        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    def _effortless_slash_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """游刃斩效果：造成6点伤害并添加剑意印记"""
        if not target:
            return False

        target.take_damage(6)
        target.add_imprint("剑意", 1)
        return True

    def _whirlwind_slash_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """回旋斩效果：造成6点伤害并添加剑意印记（只能攻击附近目标）"""
        if not target:
            return False

        target.take_damage(6)
        target.add_imprint("剑意", 1)
        return True

    def _lightning_strike_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """闪电劈效果：施加控制效果"""
        if not target:
            return False

        # 施加控制效果"lightning_strike"
        target.add_control("lightning_strike", 1)
        return True

    def _invincible_thrust_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """无敌刺效果：造成42点伤害"""
        if not target:
            return False

        target.take_damage(42)
        # 记录已对该目标使用过无敌刺
        self.invincible_strike_used.add(id(target))
        return True

    def on_behavior_change(self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]):
        """行为改变时的回调"""
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 持剑向前逼近！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 后撤步保持距离！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 运功冲破控制束缚！")

    def reset_battle_round(self):
        """重置战斗回合状态（每局开始调用）"""
        self.invincible_strike_used.clear()
        print(f"{self.name} 准备就绪，无敌刺使用记录已重置")


# 剑客技能数据库
SWORDSMAN_SKILLS_DATA = {
    "游刃斩": {
        "name": "游刃斩",
        "cooldown": 1,
        "damage": 6,
        "effect": "添加剑意印记",
        "range": "任意"
    },
    "回旋斩": {
        "name": "回旋斩",
        "cooldown": 1,
        "damage": 6,
        "effect": "添加剑意印记",
        "range": "近程",
        "special": "只能攻击附近目标"
    },
    "闪电劈": {
        "name": "闪电劈",
        "cooldown": 0,
        "damage": 0,
        "effect": "施加控制",
        "requirement": "需要目标有3层剑意印记"
    },
    "无敌刺": {
        "name": "无敌刺",
        "cooldown": 0,
        "damage": 42,
        "effect": "高额伤害",
        "requirement": "需要目标有闪电劈控制，且同一局对同一目标只能使用一次"
    }
}

# 剑客属性数据库
SWORDSMAN_STATS_DATA = {
    "name": "剑客",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "近战输出",
    "description": "擅长连击和控制的高伤害角色"
}
