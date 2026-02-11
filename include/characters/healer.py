# -*- coding: utf-8 -*-
# healer.py
from typing import Optional, Set

from core.character import Character, HARMLESS_CONTROLS
from core.skill import Skill


class Healer(Character):
    def __init__(self, name: str = "治疗师"):
        super().__init__(name, max_hp=30, control={}, stealth=0)
        # 减伤状态：剩余回合数（上限2）
        self.damage_reduction_turns: int = 0
        # 立盾系统
        self.shield_hp: int = 0
        # 记录拥有立盾期间受到的控制效果名称，用于盾碎时自动解控
        self._shield_controls: Set[str] = set()
        self._initialize_skills()

    def _initialize_skills(self):
        big_heal = Skill("大血包", cooldown=1)
        big_heal.set_effect(self._big_heal_effect)
        self.add_or_replace_skill(big_heal)

        small_heal = Skill("小血包", cooldown=1)
        small_heal.set_effect(self._small_heal_effect)
        self.add_or_replace_skill(small_heal)

        shield = Skill("套盾", cooldown=1)
        shield.set_effect(self._shield_effect)
        self.add_or_replace_skill(shield)

        fireball = Skill("大火球", cooldown=1)
        fireball.set_effect(self._fireball_effect)
        self.add_or_replace_skill(fireball)

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

    def on_turn_start(self):
        """回合开始时递减减伤状态回合数"""
        super().on_turn_start()
        if self.damage_reduction_turns > 0:
            self.damage_reduction_turns -= 1
            if self.damage_reduction_turns <= 0:
                print(f"{self.name} 的减伤状态已消失")
            else:
                print(f"{self.name} 的减伤状态剩余 {self.damage_reduction_turns} 回合")

    def take_damage(self, damage: int):
        if damage <= 0:
            print(f"{self.name} 未受到有效伤害: {damage}")
            return

        # 立盾优先承担伤害（溢出伤害不传递给本体）
        if self.shield_hp > 0:
            self.shield_hp -= damage
            if self.shield_hp <= 0:
                self.shield_hp = 0
                print(f"{self.name} 的立盾被打破！")
                # 盾碎时自动清除拥有立盾期间受到的控制效果
                self._auto_clear_shield_controls()
            else:
                print(f"{self.name} 的立盾承受了 {damage} 点伤害，立盾剩余血量: {self.shield_hp}")
            return

        # 减伤状态：最终伤害降低50%
        if self.damage_reduction_turns > 0:
            original_damage = damage
            damage = max(1, damage // 2)
            print(f"{self.name} 的减伤状态生效，伤害从 {original_damage} 降低为 {damage}")

        super().take_damage(damage)

    def add_control(self, control_name: str, stacks: int = 1):
        """重写添加控制效果，跟踪立盾期间获得的控制"""
        super().add_control(control_name, stacks)
        # 记录立盾期间受到的控制（非无害控制）
        if self.shield_hp > 0 and control_name not in HARMLESS_CONTROLS:
            self._shield_controls.add(control_name)

    def _auto_clear_shield_controls(self):
        """立盾破碎时自动清除拥有立盾期间受到的控制效果"""
        if not self._shield_controls:
            return
        controls_to_clear = set(self._shield_controls)
        self._shield_controls.clear()
        for control_name in controls_to_clear:
            if self.has_control(control_name):
                self.clear_control(control_name)
                print(f"{self.name} 的立盾破碎，自动解除了 {control_name} 控制")

    def _big_heal_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.heal(12)
        # 治疗自己时附加减伤状态（+2回合，上限2）
        if target is self:
            self.damage_reduction_turns = min(2, self.damage_reduction_turns + 2)
            print(f"{self.name} 获得减伤状态，剩余 {self.damage_reduction_turns} 回合")
        return True

    def _small_heal_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.heal(6)
        # 治疗自己时附加减伤状态（+1回合，上限2）
        if target is self:
            self.damage_reduction_turns = min(2, self.damage_reduction_turns + 1)
            print(f"{self.name} 获得减伤状态，剩余 {self.damage_reduction_turns} 回合")
        return True

    def _shield_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        # 立盾机制：生成独立立盾实体或给现有立盾增加3血量
        if isinstance(target, Healer):
            if target.shield_hp > 0:
                target.shield_hp += 3
                print(f"{target.get_name()} 的立盾增加了3点血量，当前立盾血量: {target.shield_hp}")
            else:
                target.shield_hp = 3
                target._shield_controls.clear()
                print(f"{target.get_name()} 获得了立盾，血量: {target.shield_hp}")
        else:
            # 对非治疗师目标使用：生成立盾效果（使用累积效果）
            target.add_accumulation("立盾", 3)
            print(f"{target.get_name()} 获得了立盾效果")
        return True

    def _fireball_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True


HEALER_SKILLS_DATA = {
    "大血包": {"name": "大血包", "cooldown": 2, "damage": -12, "effect": "治疗；对自己使用时附加减伤状态（+2回合，上限2回合，减伤50%）", "common": True},
    "小血包": {"name": "小血包", "cooldown": 1, "damage": -6, "effect": "治疗；对自己使用时附加减伤状态（+1回合，上限2回合，减伤50%）"},
    "套盾": {"name": "套盾", "cooldown": 1, "damage": 0, "effect": "生成立盾（3血量），叠加回复3血量；伤害优先扣立盾，溢出伤害不传递；盾碎自动解控"},
    "大火球": {"name": "大火球", "cooldown": 1, "damage": 6, "effect": "无"}
}

HEALER_STATS_DATA = {
    "name": "治疗师",
    "max_hp": 30,
    "control": {},
    "stealth": 0,
    "role_type": "治疗辅助",
    "description": "以治疗和护盾支援队友的角色"
}
