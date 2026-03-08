# -*- coding: utf-8 -*-
# warlock.py - 术士
"""
术士角色实现

技能表：
- 诅咒之剑 (CD:1) — 6伤害
- 混沌之雨 (CD:1) — 6伤害
- 死亡之门 (CD:2) — 多目标控制，每个目标均需独立解控
- 爆炸 (CD:0) — 12伤害（多目标时伤害平分）
- 六星法阵 (CD:2) — 施加控制
"""

from typing import Optional, List

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill


class Warlock(Character):
    def __init__(self, name: str = "术士"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        # 死亡之门状态追踪
        self._death_gate_active = False  # 场上是否存在死亡之门
        self._death_gate_initial_count = 0  # 本次死亡之门施加的初始目标数
        self._initialize_skills()

    def _initialize_skills(self):
        curse_sword = Skill("诅咒之剑", cooldown=1)
        curse_sword.set_effect(self._curse_sword_effect)
        self.add_or_replace_skill(curse_sword)

        chaos_rain = Skill("混沌之雨", cooldown=1)
        chaos_rain.set_effect(self._chaos_rain_effect)
        self.add_or_replace_skill(chaos_rain)

        death_gate = Skill("死亡之门", cooldown=2)
        death_gate.set_effect(self._death_gate_effect)
        self.add_or_replace_skill(death_gate)

        explosion = Skill("爆炸", cooldown=0)
        explosion.set_effect(self._explosion_effect)
        self.add_or_replace_skill(explosion)

        hex_array = Skill("六星法阵", cooldown=2)
        hex_array.set_effect(self._hex_array_effect)
        self.add_or_replace_skill(hex_array)

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

    def use_death_gate_on_targets(self, targets: List[Character]) -> bool:
        """死亡之门：对玩家选中的目标施加控制，每个目标均需独立解控"""
        skill = self.get_skill("死亡之门")
        if not skill:
            print(f"{self.name} 没有技能: 死亡之门")
            return False
        if not skill.is_available():
            print(f"技能 死亡之门 在冷却中 (CD:{skill.get_cooldown()})")
            return False
        if self._death_gate_active:
            print("场上已有死亡之门激活，无法再次使用！")
            return False
        if not targets:
            print("死亡之门没有有效目标！")
            return False

        self._death_gate_initial_count = len(targets)
        self._death_gate_active = True

        print(f"{self.name} 使用了 死亡之门！")
        for target in targets:
            target.add_control("死亡之门", 1)
            print(f"{target.get_name()} 被死亡之门束缚，需独立解控！")

        # 不在此处设置CD，待所有死亡之门解除后由外部设置CD=2
        return True

    def use_explosion_on_targets(self, targets: List[Character]) -> bool:
        """爆炸：对所有携带死亡之门的目标造成伤害（12/初始分门人数），爆炸后解除所有死亡之门。"""
        skill = self.get_skill("爆炸")
        if not skill:
            print(f"{self.name} 没有技能: 爆炸")
            return False
        if not skill.is_available():
            print(f"技能 爆炸 在冷却中 (CD:{skill.get_cooldown()})")
            return False
        if not targets:
            print("爆炸：场上没有携带死亡之门的目标！")
            return False

        initial_count = (
            self._death_gate_initial_count
            if self._death_gate_initial_count > 0
            else len(targets)
        )
        base_damage = max(1, 12 // initial_count)
        damage_per_target = self.apply_attack_buff(base_damage)

        print(
            f"{self.name} 使用了 爆炸！初始分门{initial_count}人，每人受到{damage_per_target}点伤害"
        )
        for target in targets:
            target.take_damage(damage_per_target)
            # 解除该目标的死亡之门
            target.control.pop("死亡之门", None)
            print(f"{target.get_name()} 的死亡之门已解除！")

        # 清空死亡之门状态，设置2回合冷却
        self._death_gate_active = False
        self._death_gate_initial_count = 0
        death_gate_skill = self.get_skill("死亡之门")
        if death_gate_skill:
            death_gate_skill.set_cooldown(2)

        skill.set_cooldown(skill.get_base_cooldown())
        return True

    # --- 技能效果函数 ---

    def _curse_sword_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """诅咒之剑：6点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def _chaos_rain_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """混沌之雨：6点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def _death_gate_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """死亡之门（单体入口）：施加控制"""
        if not target:
            return False
        target.add_control("死亡之门", 1)
        print(f"{target.get_name()} 被死亡之门束缚，需独立解控！")
        return True

    def _explosion_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """爆炸（单体入口）：12点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(12))
        return True

    def _hex_array_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """六星法阵：施加控制"""
        if not target:
            return False
        target.add_control("六星法阵", 1)
        return True

    def on_behavior_change(
        self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 念动咒语向前逼近！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 释放暗能后撤！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 以黑暗之力挣脱束缚！")


WARLOCK_SKILLS_DATA = {
    "诅咒之剑": {
        "name": "诅咒之剑",
        "cooldown": 1,
        "damage": 6,
        "effect": "无",
        "common": True,
    },
    "混沌之雨": {
        "name": "混沌之雨",
        "cooldown": 1,
        "damage": 6,
        "effect": "无",
    },
    "死亡之门": {
        "name": "死亡之门",
        "cooldown": 2,
        "damage": 0,
        "effect": "控制，可同时给多人，均需独立解控",
        "special": "多目标控制",
    },
    "爆炸": {
        "name": "爆炸",
        "cooldown": 0,
        "damage": 12,
        "effect": "多人中伤害平分",
        "special": "总伤害12，平分给所有目标",
    },
    "六星法阵": {
        "name": "六星法阵",
        "cooldown": 2,
        "damage": 0,
        "effect": "控制",
    },
}

WARLOCK_STATS_DATA = {
    "name": "术士",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "法术输出/控制",
    "description": "擅长诅咒与群体控制的暗系法师，爆炸技能可群体分摊伤害",
}
