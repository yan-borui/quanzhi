# -*- coding: utf-8 -*-
# scholar.py
from typing import Optional

from core.character import Character, add_burning_block
from core.skill import Skill


class Scholar(Character):
    def __init__(self, name: str = "魔道学者"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()

    def _initialize_skills(self):
        star_ray = Skill("星星射线", cooldown=1)
        star_ray.set_effect(self._star_ray_effect)
        self.add_or_replace_skill(star_ray)

        molotov = Skill("燃烧瓶", cooldown=1)
        molotov.set_effect(self._molotov_effect)
        self.add_or_replace_skill(molotov)

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

    def _star_ray_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(6)
        return True

    def _molotov_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        MOLOTOV_STACK = 1
        add_burning_block(target.block_id, MOLOTOV_STACK)
        return True


SCHOLAR_SKILLS_DATA = {
    "星星射线": {"name": "星星射线", "cooldown": 1, "damage": 6, "effect": "无", "common": True},
    "燃烧瓶": {"name": "燃烧瓶", "cooldown": 1, "damage": 3, "effect": "持续，可叠，范围，有友伤"}
}

SCHOLAR_STATS_DATA = {
    "name": "魔道学者",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "法术输出",
    "description": "用星星射线和燃烧瓶输出与控制的学者"
}
