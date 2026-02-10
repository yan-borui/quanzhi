# -*- coding: utf-8 -*-
# oil_master.py
from typing import Optional

from core.character import Character
from core.skill import Skill


class OilMaster(Character):
    def __init__(self, name: str = "卖油翁"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        self.oil_pots = 1  # 每回合只能倒一锅
        self.oil_pot_count = 0  # 油锅计数

    def _initialize_skills(self):
        pour = Skill("铜孔倒油", cooldown=1)
        pour.set_effect(self._pour_effect)
        self.add_or_replace_skill(pour)

        teach = Skill("教训你", cooldown=2)
        teach.set_effect(self._teach_effect)
        self.add_or_replace_skill(teach)

        pot = Skill("一锅油", cooldown=3)
        pot.set_effect(self._pot_effect)
        self.add_or_replace_skill(pot)

        face = Skill("倒你脸上", cooldown=0)
        face.set_effect(self._face_effect)
        self.add_or_replace_skill(face)

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

        if skill_name == "倒你脸上" and self.oil_pots <= 0:
            print("本回合已倒过油，无法再次使用倒你脸上")
            return

        # 一锅油改为瞬发自身技能，忽略target参数
        if skill_name == "一锅油":
            success = skill.execute_with_target(self, self)
        else:
            success = skill.execute_with_target(self, target)

        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")
            if skill_name == "倒你脸上":
                self.oil_pots -= 1

    def drink_oil(self, drinker: Character) -> bool:
        """喝油交互：任何角色均可执行，HP+3，消耗1个油锅计数"""
        if self.oil_pot_count <= 0:
            print(f"{self.name} 没有可用的油锅")
            return False
        self.oil_pot_count -= 1
        drinker.heal(3)
        print(f"{drinker.get_name()} 喝了 {self.name} 的油，HP+3，剩余油锅: {self.oil_pot_count}")
        return True

    def _pour_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(6)
        return True

    def _teach_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(6)
        target.add_control("教训你", 1)
        return True

    def _pot_effect(self, caster: Character, target: Optional[Character]) -> bool:
        # 瞬发技能：直接增加自身油锅计数+1
        self.oil_pot_count += 1
        print(f"{self.name} 的油锅计数 +1，当前油锅: {self.oil_pot_count}")
        return True

    def _face_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(15)
        return True

    def reset_battle_round(self):
        self.oil_pots = 1


OIL_MASTER_SKILLS_DATA = {
    "铜孔倒油": {"name": "铜孔倒油", "cooldown": 1, "damage": 6, "effect": "无", "common": True},
    "教训你": {"name": "教训你", "cooldown": 2, "damage": 6, "effect": "控制，可叠"},
    "一锅油": {"name": "一锅油", "cooldown": 3, "damage": 0, "effect": "瞬发，自身油锅计数+1；油锅可被任何角色喝（HP+3）"},
    "倒你脸上": {"name": "倒你脸上", "cooldown": 0, "damage": 15, "effect": "每次只能倒一锅"}
}

OIL_MASTER_STATS_DATA = {
    "name": "卖油翁",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "多样性输出",
    "description": "卖油翁用倒油与控制打击敌人，并提供油锅增益"
}
