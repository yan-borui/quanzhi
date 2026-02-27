# -*- coding: utf-8 -*-
# disc_master.py - 卖光盘的
"""
卖光盘的角色实现

技能表：
- 光盘 (CD:0) — 3伤害，光盘+1
- 亮瞎你 (CD:0) — 15伤害+控制，消耗3张光盘
- 光盘飞刀 (CD:0) — 30伤害，消耗5张光盘
- 光盘散落 (CD:2) — 光盘+n（n为在场玩家数）

关键机制：
- 光盘作为资源，使用 accumulation 系统管理
- 所有技能CD为0（光盘散落除外），但强力技能通过消耗光盘来平衡
- 光盘散落可根据在场玩家数量快速积累光盘资源
- 亮瞎你兼具高伤害和控制效果
"""

from typing import Optional, List

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill


class DiscMaster(Character):
    def __init__(self, name: str = "卖光盘的"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        # 光盘计数使用 accumulation 系统，键名为 "光盘"

    def _initialize_skills(self):
        disc = Skill("光盘", cooldown=0)
        disc.set_effect(self._disc_effect)
        self.add_or_replace_skill(disc)

        blind = Skill("亮瞎你", cooldown=0)
        blind.set_effect(self._blind_effect)
        self.add_or_replace_skill(blind)

        disc_knife = Skill("光盘飞刀", cooldown=0)
        disc_knife.set_effect(self._disc_knife_effect)
        self.add_or_replace_skill(disc_knife)

        disc_scatter = Skill("光盘散落", cooldown=2)
        disc_scatter.set_effect(self._disc_scatter_effect)
        self.add_or_replace_skill(disc_scatter)

    @property
    def disc_count(self) -> int:
        """当前光盘数量"""
        return self.get_accumulation("光盘")

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

        # 亮瞎你需要至少3张光盘
        if skill_name == "亮瞎你":
            if self.disc_count < 3:
                print(f"亮瞎你需要至少3张光盘！当前光盘: {self.disc_count}")
                return

        # 光盘飞刀需要至少5张光盘
        if skill_name == "光盘飞刀":
            if self.disc_count < 5:
                print(f"光盘飞刀需要至少5张光盘！当前光盘: {self.disc_count}")
                return

        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    def use_disc_scatter_with_player_count(self, player_count: int) -> bool:
        """
        光盘散落：获得n张光盘（n为在场玩家数）。
        由GameBackend调用，传入当前在场玩家数。

        Args:
            player_count: 当前在场玩家数量

        Returns:
            bool: 是否成功使用
        """
        skill = self.get_skill("光盘散落")
        if not skill:
            print(f"{self.name} 没有技能: 光盘散落")
            return False
        if not skill.is_available():
            print(f"技能 光盘散落 在冷却中 (CD:{skill.get_cooldown()})")
            return False
        if player_count <= 0:
            print("光盘散落没有有效的在场玩家！")
            return False

        self.add_accumulation("光盘", player_count)
        print(
            f"{self.name} 使用了光盘散落！获得 {player_count} 张光盘，"
            f"当前光盘: {self.disc_count}"
        )

        skill.set_cooldown(skill.get_base_cooldown())
        return True

    # --- 技能效果函数 ---

    def _disc_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """光盘：3点伤害，光盘+1"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(3))
        self.add_accumulation("光盘", 1)
        print(f"{self.name} 获得了1张光盘，当前光盘: {self.disc_count}")
        return True

    def _blind_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """亮瞎你：15点伤害+控制，消耗3张光盘"""
        if not target:
            return False

        # 消耗3张光盘
        self.reduce_accumulation("光盘", 3)
        print(f"{self.name} 消耗了3张光盘，剩余光盘: {self.disc_count}")

        target.take_damage(self.apply_attack_buff(15))
        target.add_control("亮瞎你", 1)
        print(f"{target.get_name()} 被亮瞎了！")
        return True

    def _disc_knife_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """光盘飞刀：30点伤害，消耗5张光盘"""
        if not target:
            return False

        # 消耗5张光盘
        self.reduce_accumulation("光盘", 5)
        print(f"{self.name} 消耗了5张光盘，剩余光盘: {self.disc_count}")

        target.take_damage(self.apply_attack_buff(30))
        return True

    def _disc_scatter_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """
        光盘散落（单体入口）：获得光盘。
        注意：实际使用应通过 use_disc_scatter_with_player_count 传入玩家数。
        此处作为默认入口，获取1张光盘。
        """
        self.add_accumulation("光盘", 1)
        print(f"{self.name} 散落了光盘，当前光盘: {self.disc_count}")
        return True

    def on_behavior_change(
        self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 举着光盘向前逼近！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 抱着光盘后撤！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 甩出光盘挣脱束缚！")

    def reset_battle_round(self):
        """新一局重置：清除光盘累积"""
        self.clear_accumulation("光盘")
        print(f"{self.name} 准备就绪，光盘已重置")


DISC_MASTER_SKILLS_DATA = {
    "光盘": {
        "name": "光盘",
        "cooldown": 0,
        "damage": 3,
        "effect": "光盘+1",
        "common": True,
    },
    "亮瞎你": {
        "name": "亮瞎你",
        "cooldown": 0,
        "damage": 15,
        "effect": "控制，光盘-3",
        "requirement": "需要至少3张光盘",
    },
    "光盘飞刀": {
        "name": "光盘飞刀",
        "cooldown": 0,
        "damage": 30,
        "effect": "光盘-5",
        "requirement": "需要至少5张光盘",
    },
    "光盘散落": {
        "name": "光盘散落",
        "cooldown": 2,
        "damage": 0,
        "effect": "光盘+n（n为在场玩家数）",
        "special": "资源回复",
    },
}

DISC_MASTER_STATS_DATA = {
    "name": "卖光盘的",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "资源爆发输出",
    "description": "通过积累光盘资源来释放强力技能的角色，光盘飞刀可造成巨额伤害",
}
