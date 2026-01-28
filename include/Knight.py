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
        # 无畏冲锋
        fearless_charge = Skill("无畏冲锋", cooldown=3)
        fearless_charge.set_effect(self._fearless_charge_effect)
        self.add_or_replace_skill(fearless_charge)

        # 斩
        slash = Skill("斩", cooldown=1)
        slash.set_effect(self._slash_effect)
        self.add_or_replace_skill(slash)

        # 盾
        shield = Skill("盾", cooldown=1)
        shield.set_effect(self._shield_effect)
        self.add_or_replace_skill(shield)

    def use_skill(self, skill_name: str):
        """使用技能（默认目标为自己）"""
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        """对目标使用技能"""
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return

        # 特殊处理：盾技能可以在被控时使用，也可以在死后使用
        if skill_name == "盾":
            if self.shield_charges <= 0:
                print(f"盾技能使用次数已用完！")
                return

            # 检查是否有足够的历史状态
            if len(self.state_history) < 2:
                print(f"没有足够的历史状态使用盾技能！")
                return

            # 检查上上回合是否有控制
            previous_state = self.state_history[-2]
            if previous_state.get("control", {}):
                print(f"上上回合有控制效果，无法使用盾技能！")
                return

            # 执行盾技能（不检查冷却）
            success = skill.execute_with_target(self, target)
            if success:
                print(f"{self.name} 使用了 {skill_name}")
            return

        # 其他技能需要检查冷却
        if not skill.is_available():
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return

        # 执行技能
        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    def _fearless_charge_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """无畏冲锋效果：造成12点伤害"""
        if not target:
            return False

        target.take_damage(12)
        return True

    def _slash_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """斩效果：造成3点伤害"""
        if not target:
            return False

        target.take_damage(3)
        return True

    def _shield_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """盾效果：回退到上上回合的状态（不影响行为和位置）"""
        # 消耗一次使用次数
        self.shield_charges -= 1

        # 获取上上回合的状态
        previous_state = self.state_history[-2]

        # 回退状态（不包括block_id，所以不影响行为）
        self._restore_state(previous_state)

        print(f"{self.name} 使用盾技能，状态回退到上上回合！")
        print(f"盾技能剩余使用次数: {self.shield_charges}")
        return True

    def on_turn_start(self):
        """每回合开始时调用，记录当前状态"""
        # 保存当前状态到历史记录
        current_state = self._capture_state()
        self.state_history.append(current_state)

        # 保持历史记录不超过最大大小
        if len(self.state_history) > self.max_history_size:
            self.state_history.pop(0)

        print(f"{self.name} 记录状态，历史状态数: {len(self.state_history)}")

    def _capture_state(self) -> Dict:
        """捕获当前状态（不包括block_id，避免盾影响行为）"""
        return {
            "current_hp": self.current_hp,
            "control": copy.deepcopy(self.control),
            "imprints": copy.deepcopy(self.imprints),
            "accumulations": copy.deepcopy(self.accumulations)
        }

    def _restore_state(self, state: Dict):
        """恢复状态（不恢复block_id，避免盾影响行为）"""
        self.current_hp = state["current_hp"]
        self.control = copy.deepcopy(state["control"])
        self.imprints = copy.deepcopy(state["imprints"])
        self.accumulations = copy.deepcopy(state["accumulations"])

        # 确保生命值不会超过最大值
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp

        print(f"{self.name} 状态已回退: HP={self.current_hp}, 控制={self.control}")

    def can_use_shield(self) -> bool:
        """检查是否可以使用盾技能"""
        if self.shield_charges <= 0:
            return False
        if len(self.state_history) < 2:
            return False
        previous_state = self.state_history[-2]
        if previous_state.get("control", {}):
            return False
        return True

    def on_behavior_change(self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]):
        """行为改变时的回调"""
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


# 骑士技能数据库
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
        "effect": "回退到上上回合的状态（不影响位置和行为）",
        "requirement": "需要上上回合没有控制效果，每局只能使用5次，可在被控或死后第一回合使用",
        "description": "防御性技能，可以回退状态"
    }
}

# 骑士属性数据库
KNIGHT_STATS_DATA = {
    "name": "骑士",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "防御型战士",
    "description": "拥有强大防御能力和状态回退能力的近战角色"
}