# -*- coding: utf-8 -*-
# Knight.py
import copy
from typing import Optional, Dict

from Behavior import BehaviorType
from Character import Character
from Skill import Skill


class Knight(Character):
    def __init__(self, name: str = "骑士"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        self.shield_charges = 5  # 盾技能使用次数
        self.state_history = [self._capture_state(), self._capture_state()]  # 存储最近三回合的状态
        self.max_history_size = 3  # 最大历史状态数量

    def _initialize_skills(self):
        """初始化骑士的技能"""
        fearless_charge = Skill("无畏冲锋", cooldown=3)
        fearless_charge.set_effect(self._fearless_charge_effect)
        self.add_or_replace_skill(fearless_charge)

        slash = Skill("斩", cooldown=1)
        slash.set_effect(self._slash_effect)
        self.add_or_replace_skill(slash)

        shield = Skill("盾", cooldown=1)
        shield.set_effect(self._shield_effect)
        self.add_or_replace_skill(shield)

    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return

        if skill_name == "盾":
            if self.shield_charges <= 0:
                print(f"盾技能使用次数已用完！")
                return
            if len(self.state_history) < 2:
                print(f"没有足够的历史状态使用盾技能！")
                return
            success = skill.execute_with_target(self, target)
            if success:
                print(f"{self.name} 使用了 {skill_name}")
            return

        if not skill.is_available():
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return

        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    def _fearless_charge_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(12)
        return True

    def _slash_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(3)
        return True

    def _shield_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """盾效果：移除上一回合对自己的伤害与新增控制"""
        self.shield_charges -= 1

        if len(self.turn_effects_history) < 2:
            print(f"{self.name} 没有上一回合的记录，盾无效果")
            print(f"盾技能剩余使用次数: {self.shield_charges}")
            return True  # 依旧消耗次数

        last_turn = self.turn_effects_history[-2]

        # 返还上一回合的伤害
        dmg = last_turn.get("damage", 0)
        if dmg > 0:
            self.current_hp = min(self.max_hp, self.current_hp + dmg)

        # 撤销上一回合新增的控制
        for ctrl, stacks in last_turn.get("control_add", {}).items():
            if ctrl in self.control:
                self.control[ctrl] -= stacks
                if self.control[ctrl] <= 0:
                    del self.control[ctrl]

        # 清空上一回合的记录，避免重复抵消
        self.turn_effects_history[-2] = {
            "damage": 0,
            "heal": 0,
            "control_add": {},
            "control_remove": {}
        }

        print(f"{self.name} 使用盾，抵消了上一回合的伤害与控制！ (返还{dmg}伤害)")
        print(f"盾技能剩余使用次数: {self.shield_charges}")
        return True

    def on_turn_start(self):
        """每回合开始时调用，记录当前状态"""
        current_state = self._capture_state()
        self.state_history.append(current_state)
        if len(self.state_history) > self.max_history_size:
            self.state_history.pop(0)
        print(f"{self.name} 记录状态，历史状态数: {len(self.state_history)}")

    def _capture_state(self) -> Dict:
        """捕获当前状态（不包括block_id）"""
        return {
            "current_hp": self.current_hp,
            "control": copy.deepcopy(self.control),
            "imprints": copy.deepcopy(self.imprints),
            "accumulations": copy.deepcopy(self.accumulations)
        }

    def _restore_state(self, state: Dict):
        """恢复状态（不恢复block_id）"""
        self.current_hp = state["current_hp"]
        self.control = copy.deepcopy(state["control"])
        self.imprints = copy.deepcopy(state["imprints"])
        self.accumulations = copy.deepcopy(state["accumulations"])
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp
        print(f"{self.name} 状态已回退: HP={self.current_hp}, 控制={self.control}")

    def can_use_shield(self) -> bool:
        """检查是否可以使用盾技能"""
        if self.shield_charges <= 0:
            return False
        if len(self.state_history) < 2:
            return False
        return True

    def on_behavior_change(self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 举盾冲锋！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 持盾后撤！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 集中意志抵抗控制效果！")

    def reset_battle_round(self):
        """重置战斗回合状态（每局开始调用）"""
        self.shield_charges = 5
        current_state = self._capture_state()
        self.state_history = [current_state.copy() for _ in range(self.max_history_size)]
        print(f"{self.name} 准备就绪，盾技能使用次数重置为5，历史状态已清空")


KNIGHT_SKILLS_DATA = {
    "无畏冲锋": {
        "name": "无畏冲锋",
        "cooldown": 2,
        "damage": 12,
        "effect": "无控制效果",
        "range": "任意",
        "description": "高伤害冲锋技能"
    },
    "斩": {
        "name": "斩",
        "cooldown": 0,
        "damage": 3,
        "effect": "无控制效果",
        "range": "近程",
        "description": "基础攻击技能，无冷却"
    },
    "盾": {
        "name": "盾",
        "cooldown": 0,
        "damage": 0,
        "effect": "抵消上一回合的伤害与控制（不影响位置和行为）",
        "requirement": "每局只能使用5次，可在被控或死后使用",
        "description": "防御性技能，可以抵消上一回合所受伤害与控制"
    }
}

KNIGHT_STATS_DATA = {
    "name": "骑士",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "防御型战士",
    "description": "拥有强大防御能力和状态抵消能力的近战角色"
}
