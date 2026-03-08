# -*- coding: utf-8 -*-
# scythe_worker.py - 镰刀工
"""
镰刀工角色实现

技能表：
- 飞镰 (CD:0) — 绑定目标，死时带走目标（可解控移除），对另一人使用时第一个破
- 飞镰斩 (CD:1) — 9伤害
- 黑暗飞镰 (CD:2) — 12伤害
- 挥镰 (CD:2) — 6伤害+控制，需等对方解后才可对同一人使用，对另一人使用时第一个破

使用 StateBindingSystem 实现"对另一人使用时第一个破"和"死时带走目标"机制。
"""

from typing import Optional, Set

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill
from systems.state_binding import StateBindingSystem

# 模块级共享的状态绑定系统实例，GameBackend 启动后会用自己的替换
_state_binding_system = StateBindingSystem()


class ScytheWorker(Character):
    def __init__(self, name: str = "镰刀工"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        # 挥镰使用限制追踪：记录目标仍被挥镰控制中的目标id集合
        self._swing_controlled_targets: Set[int] = set()
        # 飞镰斩→黑暗飞镰联动追踪
        self._slash_target_pending: Optional[Character] = None  # 本回合飞镰斩命中的目标
        self._dark_scythe_target: Optional[Character] = None  # 下回合可用黑暗飞镰的目标
        # 状态绑定系统引用（由GameBackend注入或使用默认）
        self.state_binding_system: StateBindingSystem = _state_binding_system

    def set_state_binding_system(self, system: StateBindingSystem):
        """由GameBackend调用注入系统级的状态绑定管理器"""
        self.state_binding_system = system

    def on_turn_start(self):
        """回合开始：将上回合飞镰斩的目标带入黑暗飞镰可用状态"""
        super().on_turn_start()
        self._dark_scythe_target = self._slash_target_pending
        self._slash_target_pending = None

    def _initialize_skills(self):
        flying_scythe = Skill("飞镰", cooldown=0)
        flying_scythe.set_effect(self._flying_scythe_effect)
        self.add_or_replace_skill(flying_scythe)

        scythe_slash = Skill("飞镰斩", cooldown=1)
        scythe_slash.set_effect(self._scythe_slash_effect)
        self.add_or_replace_skill(scythe_slash)

        dark_scythe = Skill("黑暗飞镰", cooldown=2)
        dark_scythe.set_effect(self._dark_scythe_effect)
        self.add_or_replace_skill(dark_scythe)

        swing = Skill("挥镰", cooldown=2)
        swing.set_effect(self._swing_effect)
        self.add_or_replace_skill(swing)

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

        # 挥镰特殊条件：目标仍被挥镰控制时不可再次对其使用
        if skill_name == "挥镰":
            target_id = id(target)
            if target_id in self._swing_controlled_targets:
                print(
                    f"{target.get_name()} 仍被挥镰控制中，需等其解控后才可再次使用挥镰！"
                )
                return

        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    # --- 飞镰绑定/解绑回调 ---

    def _on_flying_scythe_bind(self, source, target):
        """飞镰绑定回调：给目标添加飞镰标记控制（目标可通过解控移除）"""
        target.add_control("飞镰", 1)

    def _on_flying_scythe_unbind(self, source, target):
        """飞镰解绑回调：清除目标的飞镰标记"""
        if target.has_control("飞镰"):
            target.clear_control("飞镰")

    # --- 挥镰绑定/解绑回调 ---

    def _on_swing_bind(self, source, target):
        """挥镰绑定回调：给目标添加挥镰控制"""
        target.add_control("挥镰", 1)
        self._swing_controlled_targets.add(id(target))

    def _on_swing_unbind(self, source, target):
        """挥镰解绑回调：清除目标的挥镰控制并从追踪集合移除"""
        if target.has_control("挥镰"):
            target.clear_control("挥镰")
        self._swing_controlled_targets.discard(id(target))

    # --- 技能效果函数 ---

    def _flying_scythe_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """
        飞镰：绑定目标，死时带走目标。
        - 可解：目标解控"飞镰"后绑定自动失效
        - 对另一人使用时第一个破：StateBindingSystem的auto_unbind_old自动处理
        """
        if not target:
            return False

        self.state_binding_system.bind_state(
            skill_name="飞镰",
            source=self,
            target=target,
            on_bind=self._on_flying_scythe_bind,
            on_unbind=self._on_flying_scythe_unbind,
            state_name="飞镰",
            auto_unbind_old=True,  # 对另一人使用时自动解除旧目标
        )
        print(f"{self.name} 用飞镰锁定了 {target.get_name()}！死亡时将带走目标！")
        return True

    def _scythe_slash_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """飞镰斩：9点伤害（需目标身上有飞镰标记）"""
        if not target:
            return False
        if not target.has_control("飞镰"):
            print(f"{target.get_name()} 身上没有飞镰标记，无法使用飞镰斩！")
            return False
        target.take_damage(self.apply_attack_buff(9))
        self._slash_target_pending = target
        return True

    def _dark_scythe_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """黑暗飞镰：12点伤害（只能在飞镰斩后下一回合对同一目标使用）"""
        if not target:
            return False
        if self._dark_scythe_target is not target:
            print(f"黑暗飞镰只能对上回合被飞镰斩命中的目标使用！")
            return False
        target.take_damage(self.apply_attack_buff(12))
        self._dark_scythe_target = None
        return True

    def _swing_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """
        挥镰：6点伤害+控制。
        - 需等对方解后才可对同一人使用
        - 对另一人使用时第一个破：StateBindingSystem的auto_unbind_old自动处理
        """
        if not target:
            return False

        target.take_damage(self.apply_attack_buff(6))

        self.state_binding_system.bind_state(
            skill_name="挥镰",
            source=self,
            target=target,
            on_bind=self._on_swing_bind,
            on_unbind=self._on_swing_unbind,
            state_name="挥镰",
            auto_unbind_old=True,  # 对另一人使用时自动解除旧目标
        )
        return True

    def on_destroy(self):
        """
        镰刀工死亡时触发：
        如果飞镰仍绑定了目标，则带走目标（击杀绑定目标）。
        """
        super().on_destroy()

        # 检查飞镰绑定
        bound_target = self.state_binding_system.get_bound_target(self, "飞镰")
        if bound_target and bound_target.is_alive():
            print(f"{self.name} 死亡触发飞镰效果，带走了 {bound_target.get_name()}！")
            # 清除绑定先（避免循环触发）
            self.state_binding_system.unbind_state(self, "飞镰")
            # 击杀目标：设置HP为0并触发其死亡
            bound_target.set_current_hp(0)
            bound_target.on_destroy()
        else:
            # 没有绑定目标或目标已死，清理所有绑定
            self.state_binding_system.unbind_all_from_source(self)

    def notify_target_removed_control(self, target: Character, control_name: str):
        """
        当目标解除控制时由GameBackend调用，检查是否需要解除绑定。
        - 飞镰绑定：目标解除"飞镰"控制 → 飞镰绑定失效
        - 挥镰绑定：目标解除"挥镰"控制 → 挥镰绑定失效，允许再次对其使用
        """
        if control_name == "飞镰":
            bound = self.state_binding_system.get_bound_target(self, "飞镰")
            if bound is target:
                self.state_binding_system.unbind_state(self, "飞镰")
                print(f"{target.get_name()} 解除了飞镰锁定！")

        elif control_name == "挥镰":
            bound = self.state_binding_system.get_bound_target(self, "挥镰")
            if bound is target:
                self.state_binding_system.unbind_state(self, "挥镰")
                self._swing_controlled_targets.discard(id(target))
                print(f"{target.get_name()} 解除了挥镰控制，可再次对其使用挥镰！")

    def on_behavior_change(
        self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 挥舞镰刀向前逼近！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 后跳拉开距离！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 切断锁链挣脱束缚！")

    def reset_battle_round(self):
        """新一局重置"""
        self._swing_controlled_targets.clear()
        self._slash_target_pending = None
        self._dark_scythe_target = None
        self.state_binding_system.unbind_all_from_source(self)
        print(f"{self.name} 准备就绪，所有绑定已重置")


SCYTHE_WORKER_SKILLS_DATA = {
    "飞镰": {
        "name": "飞镰",
        "cooldown": 0,
        "damage": 0,
        "effect": "绑定目标，死时带走目标，可解，对另一人使用时第一个破",
        "common": True,
    },
    "飞镰斩": {
        "name": "飞镰斩",
        "cooldown": 1,
        "damage": 9,
        "effect": "无",
    },
    "黑暗飞镰": {
        "name": "黑暗飞镰",
        "cooldown": 2,
        "damage": 12,
        "effect": "无",
    },
    "挥镰": {
        "name": "挥镰",
        "cooldown": 2,
        "damage": 6,
        "effect": "控制，需等对方解后才可对同一人再用，对另一人使用时第一个破",
    },
}

SCYTHE_WORKER_STATS_DATA = {
    "name": "镰刀工",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "绑定/控制输出",
    "description": "以飞镰锁定敌人，死亡时可带走目标的特殊角色",
}
