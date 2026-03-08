# -*- coding: utf-8 -*-
# chicken_master.py - 吃鸡大师
"""
吃鸡大师角色实现

技能表：
- 落地成盒 (CD:2) — 12伤害
- M4扫射 (CD:1) — 6伤害
- 烟雾弹 (CD:2) — 控制（使目标进入烟雾状态）
- 空投 (CD:0) — 获得1个空投资源

关键机制：
- 空投作为资源，使用 accumulation 系统管理
- 拥有 n (n≥4) 个空投时可复活，复活后血量为 3n
- 复活机制在 on_destroy 中标记，由 GameBackend 检测并执行
- 非常用角色（否），但有独特的复活机制
"""

from typing import Optional

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill


class ChickenMaster(Character):
    def __init__(self, name: str = "吃鸡大师"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        # 复活待处理标记
        self._pending_revive = False
        self._revive_hp = 0

    def _initialize_skills(self):
        landing_box = Skill("落地成盒", cooldown=2)
        landing_box.set_effect(self._landing_box_effect)
        self.add_or_replace_skill(landing_box)

        m4_spray = Skill("M4扫射", cooldown=1)
        m4_spray.set_effect(self._m4_spray_effect)
        self.add_or_replace_skill(m4_spray)

        smoke = Skill("烟雾弹", cooldown=2)
        smoke.set_effect(self._smoke_effect)
        self.add_or_replace_skill(smoke)

        airdrop = Skill("空投", cooldown=0)
        airdrop.set_effect(self._airdrop_effect)
        self.add_or_replace_skill(airdrop)

    @property
    def airdrop_count(self) -> int:
        """当前空投数量"""
        return self.get_accumulation("空投")

    def can_revive(self) -> bool:
        """检查是否可以复活（拥有 n≥4 个空投）"""
        return self.airdrop_count >= 4

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

    # --- 技能效果函数 ---

    def _landing_box_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """落地成盒：12点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(12))
        return True

    def _m4_spray_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """M4扫射：6点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def _smoke_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """烟雾弹：施加控制"""
        if not target:
            return False
        target.add_control("烟雾弹", 1)
        print(f"{target.get_name()} 被烟雾弹笼罩！")
        return True

    def _airdrop_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """空投：获得1个空投资源"""
        self.add_accumulation("空投", 1)
        print(f"{self.name} 获得了1个空投，当前空投: {self.airdrop_count}")
        return True

    def on_destroy(self):
        """
        吃鸡大师死亡时触发：
        如果拥有 n≥4 个空投，标记复活待处理。
        复活后血量为 3n，清除所有空投。
        """
        if self.can_revive():
            n = self.airdrop_count
            self._revive_hp = 3 * n
            self._pending_revive = True
            print(
                f"{self.name} 死亡！但拥有 {n} 个空投，即将复活！"
                f"复活血量: {self._revive_hp}"
            )
            # 消耗所有空投
            self.clear_accumulation("空投")
        else:
            self._pending_revive = False
            super().on_destroy()

    def try_revive(self) -> bool:
        """
        尝试执行复活。由 GameBackend 在更新存活角色时调用。

        Returns:
            bool: 是否成功复活
        """
        if self._pending_revive and self._revive_hp > 0:
            self._pending_revive = False
            # 设置新的最大生命值和当前生命值
            revive_hp = self._revive_hp
            self._revive_hp = 0
            self.max_hp = revive_hp
            self.current_hp = revive_hp
            print(
                f"{self.name} 通过空投复活！"
                f"当前生命值: {self.current_hp}/{self.max_hp}"
            )
            return True
        return False

    @property
    def pending_revive(self) -> bool:
        """是否有待处理的复活"""
        return self._pending_revive

    def on_behavior_change(
        self,
        old_behavior: Optional[BehaviorType],
        new_behavior: Optional[BehaviorType],
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 端着M4向前逼近！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 找掩体后撤！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 从烟雾中挣脱！")

    def reset_battle_round(self):
        """新一局重置：清除空投累积"""
        self.clear_accumulation("空投")
        self._pending_revive = False
        self._revive_hp = 0
        print(f"{self.name} 准备就绪，空投已重置")


CHICKEN_MASTER_SKILLS_DATA = {
    "落地成盒": {
        "name": "落地成盒",
        "cooldown": 2,
        "damage": 12,
        "effect": "无",
        "common": False,
    },
    "M4扫射": {
        "name": "M4扫射",
        "cooldown": 1,
        "damage": 6,
        "effect": "无",
    },
    "烟雾弹": {
        "name": "烟雾弹",
        "cooldown": 2,
        "damage": 0,
        "effect": "控制",
    },
    "空投": {
        "name": "空投",
        "cooldown": 0,
        "damage": 0,
        "effect": "空投+1",
        "special": "拥有n(n≥4)个空投时可复活，复活血量3n",
    },
}

CHICKEN_MASTER_STATS_DATA = {
    "name": "吃鸡大师",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "资源/复活",
    "description": "通过积累空投资源获得复活能力的角色，拥有4个以上空投时死亡可复活",
}
