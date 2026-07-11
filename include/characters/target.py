# -*- coding: utf-8 -*-
# target.py
from core.event_log import emit
from typing import Optional

from core.character import Character
from core.skill import Skill


class Target(Character):
    def __init__(self, name: str = "靶子"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()

    def _initialize_skills(self):
        basic_attack = Skill("平A", cooldown=0)
        basic_attack.set_effect(self._basic_attack_effect)
        self.add_or_replace_skill(basic_attack)

    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        self.execute_skill_action(skill_name, target)

    def _basic_attack_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True


TARGET_SKILLS_DATA = {
    "平A": {
        "name": "平A",
        "cooldown": 0,
        "damage": 6,
        "effect": "基础攻击",
        "range": "任意",
    }
}

TARGET_STATS_DATA = {
    "name": "靶子",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "练习目标",
    "description": "只有基础攻击的练习靶子",
}
