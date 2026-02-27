# -*- coding: utf-8 -*-
# ninja.py - 忍者
"""
忍者角色实现

技能表：
- 樱花岁月 (CD:2) — 12伤害，使用后破除铁索覆身绑定
- 铁索覆身 (CD:0) — 控制，对另一人使用时第一个破，使用樱花岁月或忍法地心时破
- 摔 (CD:0) — 6伤害，需有铁索覆身绑定在目标身上
- 忍法地心 (CD:2) — 进入隐身，对手需"搜索"并经过判定才能找出
- 偷袭 (CD:0) — 6伤害，需处于忍法地心隐身状态

关键机制：
- 铁索覆身使用 StateBindingSystem 实现"对另一人使用时第一个破"
- 忍法地心使用 stealth 属性 + DualJudgmentSystem 判定
- 使用樱花岁月或忍法地心时自动破除铁索覆身
"""

from typing import Optional

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill
from systems.state_binding import StateBindingSystem
from systems.dual_judgment import DualJudgmentSystem, JudgmentResult

# 模块级共享实例，GameBackend 启动后会注入自己的
_state_binding_system = StateBindingSystem()
_dual_judgment_system = DualJudgmentSystem()


class Ninja(Character):
    def __init__(self, name: str = "忍者"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        # 系统引用（由GameBackend注入或使用默认）
        self.state_binding_system: StateBindingSystem = _state_binding_system
        self.dual_judgment_system: DualJudgmentSystem = _dual_judgment_system
        # 忍法地心状态标记
        self._in_stealth = False

    def set_state_binding_system(self, system: StateBindingSystem):
        """由GameBackend调用注入系统级的状态绑定管理器"""
        self.state_binding_system = system

    def set_dual_judgment_system(self, system: DualJudgmentSystem):
        """由GameBackend调用注入系统级的判定系统"""
        self.dual_judgment_system = system

    def _initialize_skills(self):
        sakura = Skill("樱花岁月", cooldown=2)
        sakura.set_effect(self._sakura_effect)
        self.add_or_replace_skill(sakura)

        chain = Skill("铁索覆身", cooldown=0)
        chain.set_effect(self._chain_effect)
        self.add_or_replace_skill(chain)

        throw = Skill("摔", cooldown=0)
        throw.set_effect(self._throw_effect)
        self.add_or_replace_skill(throw)

        stealth = Skill("忍法地心", cooldown=2)
        stealth.set_effect(self._stealth_effect)
        self.add_or_replace_skill(stealth)

        sneak_attack = Skill("偷袭", cooldown=0)
        sneak_attack.set_effect(self._sneak_attack_effect)
        self.add_or_replace_skill(sneak_attack)

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

        # 摔的条件检查：目标必须有铁索覆身控制
        if skill_name == "摔":
            bound_target = self.state_binding_system.get_bound_target(self, "铁索覆身")
            if bound_target is not target or not target.has_control("铁索覆身"):
                print(f"摔需要目标被铁索覆身锁定！")
                return

        # 偷袭的条件检查：必须处于忍法地心隐身
        if skill_name == "偷袭":
            if not self._in_stealth:
                print(f"偷袭需要先使用忍法地心进入隐身状态！")
                return

        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    # --- 铁索覆身绑定/解绑回调 ---

    def _on_chain_bind(self, source, target):
        """铁索覆身绑定回调：给目标添加铁索覆身控制"""
        target.add_control("铁索覆身", 1)

    def _on_chain_unbind(self, source, target):
        """铁索覆身解绑回调：清除目标的铁索覆身控制"""
        if target.has_control("铁索覆身"):
            target.clear_control("铁索覆身")

    def _break_chain_binding(self):
        """破除铁索覆身绑定（樱花岁月或忍法地心使用时调用）"""
        if self.state_binding_system.is_bound(self, "铁索覆身"):
            print(f"{self.name} 使用技能，铁索覆身绑定被破除！")
            self.state_binding_system.unbind_state(self, "铁索覆身")

    # --- 技能效果函数 ---

    def _sakura_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """樱花岁月：12点伤害，使用后破除铁索覆身"""
        if not target:
            return False

        # 使用樱花岁月会破除铁索覆身
        self._break_chain_binding()

        target.take_damage(self.apply_attack_buff(12))
        return True

    def _chain_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """
        铁索覆身：控制目标。
        - 对另一人使用时第一个破（auto_unbind_old）
        - 使用樱花岁月或忍法地心时破
        """
        if not target:
            return False

        self.state_binding_system.bind_state(
            skill_name="铁索覆身",
            source=self,
            target=target,
            on_bind=self._on_chain_bind,
            on_unbind=self._on_chain_unbind,
            state_name="铁索覆身",
            auto_unbind_old=True,  # 对另一人使用时自动解除旧目标
        )
        print(f"{self.name} 用铁索覆身锁定了 {target.get_name()}！")
        return True

    def _throw_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """摔：6点伤害，需有铁索覆身在目标身上"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def _stealth_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """
        忍法地心：进入隐身状态。
        - 使用后破除铁索覆身
        - 设置stealth=1，对手需找→判定
        """
        # 使用忍法地心会破除铁索覆身
        self._break_chain_binding()

        self._in_stealth = True
        self.stealth = 1
        print(f"{self.name} 使用忍法地心，遁入地中隐身！")
        return True

    def _sneak_attack_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """偷袭：6点伤害，需处于忍法地心隐身"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def be_searched(self, searcher: Character) -> bool:
        """
        被搜索时的判定逻辑。
        由GameBackend调用，searcher消耗行动回合搜索忍者。
        使用DualJudgmentSystem进行猜拳判定。

        Args:
            searcher: 执行搜索的角色

        Returns:
            bool: 是否成功找出忍者
        """
        if not self._in_stealth:
            print(f"{self.name} 当前未隐身，无需搜索")
            return True

        print(f"{searcher.get_name()} 正在搜索 {self.name}...")

        result = self.dual_judgment_system.judge(searcher, self, "忍法地心")

        if result == JudgmentResult.INITIATOR_WIN:
            # 搜索者获胜，忍者被找出
            self._in_stealth = False
            self.stealth = 0
            print(f"{searcher.get_name()} 成功找出了 {self.name}！忍者脱离隐身！")
            return True
        else:
            # 忍者获胜，继续隐身
            print(f"{searcher.get_name()} 未能找到 {self.name}，忍者继续隐身！")
            return False

    def be_found_directly(self, finder: Character):
        """
        被直接找出（无需判定，如机械师的电子眼效果）。
        """
        if self._in_stealth:
            self._in_stealth = False
            self.stealth = 0
            print(f"{self.name} 被 {finder.get_name()} 直接找出！")

    @property
    def in_stealth(self) -> bool:
        """是否处于隐身状态"""
        return self._in_stealth

    def notify_target_removed_control(self, target: Character, control_name: str):
        """
        当目标解除控制时由GameBackend调用。
        - 铁索覆身：目标解除"铁索覆身"控制 → 绑定失效
        """
        if control_name == "铁索覆身":
            bound = self.state_binding_system.get_bound_target(self, "铁索覆身")
            if bound is target:
                self.state_binding_system.unbind_state(self, "铁索覆身")
                print(f"{target.get_name()} 挣脱了铁索覆身！")

    def take_damage(self, damage: int):
        """受伤时脱离隐身"""
        if self._in_stealth and damage > 0:
            self._in_stealth = False
            self.stealth = 0
            print(f"{self.name} 受到伤害，脱离隐身状态！")
        super().take_damage(damage)

    def on_behavior_change(
        self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 悄然潜近！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 施展轻功后撤！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 运用忍术挣脱束缚！")

    def reset_battle_round(self):
        """新一局重置"""
        self._in_stealth = False
        self.stealth = 0
        self.state_binding_system.unbind_all_from_source(self)
        print(f"{self.name} 准备就绪，所有状态已重置")


NINJA_SKILLS_DATA = {
    "樱花岁月": {
        "name": "樱花岁月",
        "cooldown": 2,
        "damage": 12,
        "effect": "无，使用后破除铁索覆身",
        "common": True,
    },
    "铁索覆身": {
        "name": "铁索覆身",
        "cooldown": 0,
        "damage": 0,
        "effect": "控制，对另一人使用时第一个破，使用樱花岁月或忍法地心时破",
    },
    "摔": {
        "name": "摔",
        "cooldown": 0,
        "damage": 6,
        "effect": "需有铁索覆身在目标身上",
        "requirement": "目标必须被铁索覆身控制",
    },
    "忍法地心": {
        "name": "忍法地心",
        "cooldown": 2,
        "damage": 0,
        "effect": "进入隐身，对手需搜索并判定才能找出",
        "special": "使用后破除铁索覆身",
    },
    "偷袭": {
        "name": "偷袭",
        "cooldown": 0,
        "damage": 6,
        "effect": "需处于忍法地心隐身状态",
        "requirement": "需要忍法地心隐身",
    },
}

NINJA_STATS_DATA = {
    "name": "忍者",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "潜行/控制",
    "description": "擅长隐身与铁索控制的忍者，可在暗处发动偷袭",
}
