# -*- coding: utf-8 -*-
# ranger.py
from typing import Optional

from core.character import Character
from core.skill import Skill


class Ranger(Character):
    def __init__(self, name: str = "游侠"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()

    def _initialize_skills(self):
        brick = Skill("板砖", cooldown=0)
        brick.set_effect(self._brick_effect)
        self.add_or_replace_skill(brick)

        sandbag = Skill("纱袋", cooldown=1)
        sandbag.set_effect(self._sandbag_effect)
        self.add_or_replace_skill(sandbag)

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

    def _brick_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        damage = 6 if self.is_nearby(target) else 3
        target.take_damage(self.apply_attack_buff(damage))
        return True

    def _sandbag_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        if target.has_control("纱袋"):
            print(f"{target.get_name()} 已被纱袋控制，无法叠加")
            return False
        target.add_control("纱袋", 1)
        # 强制位移：将目标移动到游侠所在的地块
        target.set_block_id(self.block_id)
        print(f"{target.get_name()} 被强制位移到 {self.name} 所在的地块")
        return True


RANGER_SKILLS_DATA = {
    "板砖": {
        "name": "板砖",
        "cooldown": 0,
        "damage": "远程3/近程6",
        "effect": "无控制效果",
        "range": "远程/近程",
        "common": True
    },
    "纱袋": {
        "name": "纱袋",
        "cooldown": 1,
        "damage": 0,
        "effect": "控制（不可叠）+ 强制位移至游侠所在地块",
        "range": "任意",
        "common": False
    }
}

RANGER_STATS_DATA = {
    "name": "游侠",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "远程/近程灵活输出",
    "description": "以板砖和控制技能牵制敌人的游侠"
}
