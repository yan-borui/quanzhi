# -*- coding: utf-8 -*-
# healer.py
from typing import Optional

from core.character import Character
from core.skill import Skill


class Healer(Character):
    def __init__(self, name: str = "治疗师"):
        super().__init__(name, max_hp=30, control={}, stealth=0)
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

    def _big_heal_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.heal(12)
        return True

    def _small_heal_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.heal(6)
        return True

    def _shield_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.add_control("护盾", 1)
        return True

    def _fireball_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(6)
        return True


HEALER_SKILLS_DATA = {
    "大血包": {"name": "大血包", "cooldown": 2, "damage": -12, "effect": "治疗", "common": True},
    "小血包": {"name": "小血包", "cooldown": 1, "damage": -6, "effect": "治疗"},
    "套盾": {"name": "套盾", "cooldown": 1, "damage": 0, "effect": "给一个单位护盾，抵消一次攻击"},
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
