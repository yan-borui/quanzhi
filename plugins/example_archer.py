# -*- coding: utf-8 -*-
"""
示例插件 - 弓箭手角色
将此文件放到 plugins/ 目录下即可自动加载

每个插件文件需要导出:
- 一个继承 Character 的角色类
- ROLE_ID: 角色唯一标识符（可选，默认使用文件名）
- STATS_DATA: 角色元数据字典（可选）
"""

from typing import Optional

from core.character import Character
from core.skill import Skill


ROLE_ID = "archer"


class Archer(Character):
    def __init__(self, name: str = "弓箭手"):
        super().__init__(name, max_hp=50, control={}, stealth=0)
        self._initialize_skills()
        self.arrow_count = 10

    def _initialize_skills(self):
        normal_shot = Skill("普通射击", cooldown=0)
        normal_shot.set_effect(self._normal_shot_effect)
        self.add_or_replace_skill(normal_shot)

        pierce_arrow = Skill("穿透箭", cooldown=2)
        pierce_arrow.set_effect(self._pierce_arrow_effect)
        self.add_or_replace_skill(pierce_arrow)

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

    def _normal_shot_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(5)
        return True

    def _pierce_arrow_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        if self.arrow_count < 3:
            return False
        self.arrow_count -= 3
        target.take_damage(15)
        print(f"{self.name} 消耗3支箭，剩余{self.arrow_count}支")
        return True


STATS_DATA = {
    "name": "弓箭手",
    "max_hp": 50,
    "control": {},
    "stealth": 0,
    "role_type": "远程输出",
    "description": "擅长远程攻击的灵活角色（示例插件）"
}
