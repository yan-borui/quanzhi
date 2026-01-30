# -*- coding: utf-8 -*-
# array_master.py
from typing import Optional, Callable

from core.character import Character
from core.skill import Skill


class ArrayMaster(Character):
    def __init__(self, name: str = "阵鬼"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()

    def _initialize_skills(self):
        skill_defs = {
            "瘟阵": 0,
            "灰阵": 0,
            "风阵": 0,
            "火阵": 2,
            "五彩法阵": 0
        }
        for skill_name, cd in skill_defs.items():
            skill = Skill(skill_name, cooldown=cd)
            skill.set_effect(getattr(self, f"_{skill_name}_effect"))
            self.add_or_replace_skill(skill)

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

    def _add_array_control(self, target: Character, name: str, control_key: str, extra: Optional[Callable[[], None]] = None):
        if target.has_control(control_key):
            print(f"{target.get_name()} 已有{control_key}控制，无法叠加")
            return False
        target.add_control(control_key, 1)
        if extra:
            extra()
        return True

    def _瘟阵_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        return self._add_array_control(target, "瘟阵", "瘟阵")

    def _灰阵_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        return self._add_array_control(target, "灰阵", "灰阵")

    def _风阵_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        return self._add_array_control(target, "风阵", "风阵")

    def _火阵_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        return self._add_array_control(target, "火阵", "火阵", lambda: target.take_damage(2))

    def _五彩法阵_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        required = ["瘟阵", "灰阵", "风阵", "火阵"]
        if not all(target.has_control(c) for c in required):
            print(f"{target.get_name()} 缺少必要的四个阵，无法发动五彩法阵")
            return False
        target.take_damage(60)
        return True


ARRAY_MASTER_SKILLS_DATA = {
    "瘟阵": {"name": "瘟阵", "cooldown": 0, "damage": 0, "effect": "控制，不可叠", "common": True},
    "灰阵": {"name": "灰阵", "cooldown": 0, "damage": 0, "effect": "控制，不可叠"},
    "风阵": {"name": "风阵", "cooldown": 0, "damage": 0, "effect": "控制，不可叠，近程控，目标不能使用近程技能"},
    "火阵": {"name": "火阵", "cooldown": 2, "damage": 0, "effect": "持续，不可叠"},
    "五彩法阵": {"name": "五彩法阵", "cooldown": 0, "damage": 60, "effect": "需四阵齐全并判定"}
}

ARRAY_MASTER_STATS_DATA = {
    "name": "阵鬼",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "控制型",
    "description": "布阵削弱敌人并引爆五彩法阵的控制型角色"
}
