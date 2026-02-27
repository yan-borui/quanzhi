# -*- coding: utf-8 -*-
"""
Character 抽象基类
- 提取 Player 和 Summon 的公共属性与方法
- 管理：生命值、控制、潜行、技能、印记（imprints）和累积效果（accumulations）
- 提供边界检查：map 访问、hp 范围、印记/累积减值不越界、技能检查等

设计说明：
- 只包含与角色状态与技能管理相关的通用逻辑，具体的 use_skill() 为抽象方法。
- 技能容器以 dict[name, Skill] 保存（值语义），避免频繁 new/delete。

改进点：
- 使用 Optional 提供更安全的技能访问
- 增加了类型注解
- 改进了摧毁状态的检测逻辑
- 添加了行为系统和邻接表管理
- 修改is_nearby为基于block_id判断，避免邻接表不同步
- 死亡时自动清除所有控制效果
- 新增回合事件记录（伤害/治疗/控制增减），供骑士盾等效果使用
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, List
from threading import Lock
from core.skill import Skill
from core.behavior import BehaviorType

HARMLESS_CONTROLS = {"护盾", "风阵", "燃烧瓶", "火阵"}

BURNING_BLOCKS: Dict[int, int] = {}
BURNING_BLOCKS_LOCK = Lock()


def add_burning_block(block_id: int, stacks: int = 1):
    if stacks <= 0:
        return
    with BURNING_BLOCKS_LOCK:
        BURNING_BLOCKS[block_id] = BURNING_BLOCKS.get(block_id, 0) + stacks


def get_burning_block_stacks(block_id: int) -> int:
    with BURNING_BLOCKS_LOCK:
        return BURNING_BLOCKS.get(block_id, 0)


class Character(ABC):
    def __init__(
        self,
        name: str = "",
        max_hp: int = 0,
        control: Dict[str, int] = None,
        stealth: int = 0,
    ):
        self.name = name
        self.max_hp = max(0, max_hp)
        self.current_hp = max(0, self.max_hp)
        self.control = control if control is not None else {}
        self.stealth = stealth
        self.block_id = id(self)

        self.skills: Dict[str, Skill] = {}
        self.imprints: Dict[str, int] = {}
        self.accumulations: Dict[str, int] = {}
        self.nearby_characters: List["Character"] = [self]
        self.current_behavior: Optional[BehaviorType] = None

        # 每回合的事件记录（只保留最近两个回合）
        self.turn_effects_history: List[Dict] = []

    # 子类必须实现技能使用
    @abstractmethod
    def use_skill(self, skill_name: str):
        pass

    def start_new_turn_log(self):
        """开始新回合时调用，创建一条新的事件记录"""
        self.turn_effects_history.append(
            {
                "damage": 0,
                "heal": 0,
                "control_add": {},  # name -> stacks
                "control_remove": {},  # name -> stacks
                "imprint_add": {},
            }
        )
        # 只保留最近两个回合的记录
        if len(self.turn_effects_history) > 2:
            self.turn_effects_history.pop(0)

    def _current_turn_log(self) -> Dict:
        if not self.turn_effects_history:
            self.start_new_turn_log()
        return self.turn_effects_history[-1]

    def get_block_id(self) -> int:
        """获取角色所在的块ID"""
        return self.block_id

    def set_block_id(self, block_id: int):
        """设置角色所在的块ID"""
        self.block_id = block_id

    def is_controlled(self) -> bool:
        """检查角色是否被控制（有控制效果）"""
        # 护盾/风阵/燃烧瓶/火阵不阻止行动
        return any(k not in HARMLESS_CONTROLS for k in self.control.keys())

    # 带目标的技能使用（可选实现）
    def use_skill_on_target(self, skill_name: str, target: "Character"):
        # 默认实现忽略目标，子类可以重写
        self.use_skill(skill_name)

    def set_behavior(self, behavior: BehaviorType):
        """设置当前行为"""
        old_behavior = self.current_behavior
        self.current_behavior = behavior
        self.on_behavior_change(old_behavior, behavior)

    def get_behavior(self) -> Optional[BehaviorType]:
        """获取当前行为"""
        return self.current_behavior

    def on_behavior_change(
        self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]
    ):
        """行为改变时的回调，子类可重写"""
        pass

    # 邻接表管理
    def add_nearby_character(self, character: "Character"):
        """添加附近角色"""
        if character != self and character not in self.nearby_characters:
            self.nearby_characters.append(character)
            if self not in character.nearby_characters:
                character.add_nearby_character(self)
            print(f"{self.name} 与 {character.name} 距离变近")

    def remove_nearby_character(self, character: "Character"):
        """移除附近角色"""
        if character in self.nearby_characters:
            self.nearby_characters.remove(character)
            if self in character.nearby_characters:
                character.remove_nearby_character(self)
            print(f"{self.name} 与 {character.name} 距离变远")

    def clear_nearby_characters(self):
        """清空附近角色列表"""
        for character in list(self.nearby_characters):
            self.remove_nearby_character(character)

    def get_nearby_characters(self) -> List["Character"]:
        """获取附近角色列表"""
        return list(self.nearby_characters)

    def is_nearby(self, character: "Character") -> bool:
        """检查是否在某个角色附近（基于block_id判断，避免邻接表不同步）"""
        return self.block_id == character.block_id

    def apply_attack_buff(self, base_damage: int) -> int:
        """应用攻击强化效果并消耗，返回最终伤害值"""
        buff = self.get_accumulation("攻击强化")
        if buff > 0:
            print(f"{self.name} 的攻击强化效果生效，伤害增加 {buff} 点")
            self.clear_accumulation("攻击强化")
            return base_damage + buff
        return base_damage

    # 受伤并显示（确保边界）
    def take_damage(self, damage: int):
        if damage <= 0:
            print(f"{self.name} 未受到有效伤害: {damage}")
            return

        # 单次护盾效果：抵消一次攻击后消失
        if self.has_control("护盾"):
            self.clear_control("护盾")
            print(f"{self.name} 的护盾抵消了这次攻击！")
            return

        # 易伤效果：受到伤害增加，然后消耗易伤
        vulnerability = self.get_accumulation("易伤")
        if vulnerability > 0:
            bonus = damage * vulnerability // 100
            damage += bonus
            print(f"{self.name} 的易伤效果生效，伤害增加 {bonus} 点")
            self.clear_accumulation("易伤")

        was_alive = self.is_alive()
        self.current_hp -= damage
        if self.current_hp < 0:
            self.current_hp = 0

        # 记录本回合受到的伤害
        self._current_turn_log()["damage"] += damage

        print(
            f"{self.name} 受到了 {damage} 点伤害，当前生命值: {self.current_hp}/{self.max_hp}"
        )

        if was_alive and self.is_destroyed():
            if self.control:
                print(f"{self.name} 死亡时清除了所有控制效果")
                self.clear_all_controls()
            self.on_destroy()

    # 治疗并显示
    def heal(self, amount: int):
        if amount <= 0:
            print(f"{self.name} 没有被有效治疗: {amount}")
            return
        self.current_hp += amount
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp

        # 记录本回合治疗
        self._current_turn_log()["heal"] += amount

        print(
            f"{self.name} 恢复了 {amount} 点生命值，当前生命值: {self.current_hp}/{self.max_hp}"
        )

    # 技能管理
    def has_skill(self, skill_name: str) -> bool:
        return skill_name in self.skills

    def get_skill_cooldown(self, skill_name: str) -> int:
        if skill_name in self.skills:
            return self.skills[skill_name].get_cooldown()
        return -1

    def set_skill_cooldown(self, skill_name: str, cooldown: int):
        if skill_name in self.skills:
            self.skills[skill_name].set_cooldown(cooldown)

    def reduce_all_cooldowns(self):
        for skill in self.skills.values():
            skill.reduce_cooldown()

    def increase_all_cooldowns(self):
        for skill in self.skills.values():
            current_cd = skill.get_cooldown()
            base_cd = skill.get_base_cooldown()
            if current_cd < base_cd:
                skill.set_cooldown(current_cd + 1)

    def add_or_replace_skill(self, skill: Skill):
        if not skill.get_name():
            return
        self.skills[skill.get_name()] = skill

    def add_or_replace_skill_copy(self, skill: Skill):
        if not skill.get_name():
            return
        self.skills[skill.get_name()] = Skill(
            skill.get_name(), skill.get_base_cooldown()
        )

    def get_skill(self, skill_name: str) -> Optional[Skill]:
        return self.skills.get(skill_name)

    # 控制效果管理
    def add_control(self, control_name: str, stacks: int = 1):
        """添加控制效果"""
        if not control_name or stacks <= 0:
            return
        if control_name in self.control:
            self.control[control_name] += stacks
        else:
            self.control[control_name] = stacks

        # 记录本回合新增控制
        log = self._current_turn_log()
        log["control_add"][control_name] = (
            log["control_add"].get(control_name, 0) + stacks
        )

        print(
            f"{self.name} 获得了 {control_name} 控制效果，层数: {self.control[control_name]}"
        )

    def get_control(self, control_name: str = None) -> int:
        if control_name:
            return self.control.get(control_name, 0)
        else:
            return sum(self.control.values())

    def has_control(self, control_name: str) -> bool:
        return self.get_control(control_name) > 0

    def reduce_control(self, control_name: str, stacks: int = 1):
        """减少控制效果层数"""
        if control_name not in self.control or stacks <= 0:
            print(f"{self.name} 没有控制效果: {control_name}")
            return

        removed = min(stacks, self.control[control_name])
        self.control[control_name] -= stacks
        if self.control[control_name] <= 0:
            del self.control[control_name]
            print(f"{self.name} 清除了 {control_name} 控制效果")
        else:
            print(
                f"{self.name} 减少了 {control_name} 控制效果，剩余层数: {self.control[control_name]}"
            )

        # 记录本回合移除控制
        log = self._current_turn_log()
        log["control_remove"][control_name] = (
            log["control_remove"].get(control_name, 0) + removed
        )

    def clear_control(self, control_name: str):
        """清除特定的控制效果"""
        if control_name in self.control:
            stacks = self.control.get(control_name, 0)
            # 记录移除
            log = self._current_turn_log()
            log["control_remove"][control_name] = (
                log["control_remove"].get(control_name, 0) + stacks
            )

            del self.control[control_name]
            print(f"{self.name} 清除了 {control_name} 控制效果")

    def clear_all_controls(self):
        """清除所有控制效果"""
        if self.control:
            log = self._current_turn_log()
            for control_name, stacks in self.control.items():
                log["control_remove"][control_name] = (
                    log["control_remove"].get(control_name, 0) + stacks
                )
        self.control.clear()

    # 印记管理
    def add_imprint(self, imprint: str, value: int):
        if not imprint:
            return
        current_value = self.imprints.get(imprint, 0)
        self.imprints[imprint] = current_value + value

        # 记录本回合新增印记
        if value > 0:
            log = self._current_turn_log()
            log["imprint_add"][imprint] = log["imprint_add"].get(imprint, 0) + value

        print(
            f"{self.name} 获得了 {imprint} 印记，值: {value}，当前值: {self.imprints[imprint]}"
        )

    def get_imprint(self, imprint: str) -> int:
        return self.imprints.get(imprint, 0)

    def remove_imprint(self, imprint: str):
        if imprint not in self.imprints:
            print(f"{self.name} 不存在印记: {imprint}")
            return

        if self.imprints[imprint] > 1:
            self.imprints[imprint] -= 1
            print(
                f"{self.name} 移除了一层 {imprint} 印记，剩余: {self.imprints[imprint]}"
            )
        else:
            del self.imprints[imprint]
            print(f"{self.name} 清除了 {imprint} 印记")

    def clear_imprint(self, imprint: str):
        if imprint in self.imprints:
            del self.imprints[imprint]
            print(f"{self.name} 清除了 {imprint} 累积效果")

    # 累积效果管理
    def add_accumulation(self, effect: str, value: int):
        if not effect:
            return
        if effect not in self.accumulations:
            self.accumulations[effect] = 0
        self.accumulations[effect] += value
        print(f"{self.name} 获得了 {effect} 累积效果，值: {self.accumulations[effect]}")

    def get_accumulation(self, effect: str) -> int:
        return self.accumulations.get(effect, 0)

    def reduce_accumulation(self, effect: str, number: int):
        if effect not in self.accumulations:
            print(f"{self.name} 没有累积效果: {effect}")
            return

        self.accumulations[effect] -= number
        if self.accumulations[effect] <= 0:
            del self.accumulations[effect]
            print(f"{self.name} 消耗并清除了 {effect} 累积效果")
        else:
            print(
                f"{self.name} 消耗了 {effect} 累积效果，剩余: {self.accumulations[effect]}"
            )

    def clear_accumulation(self, effect: str):
        if effect in self.accumulations:
            del self.accumulations[effect]
            print(f"{self.name} 清除了 {effect} 累积效果")

    # 属性访问与设置
    def get_current_hp(self) -> int:
        return self.current_hp

    def get_max_hp(self) -> int:
        return self.max_hp

    def get_control_dict(self) -> Dict[str, int]:
        return self.control.copy()

    def get_stealth(self) -> int:
        return self.stealth

    def get_name(self) -> str:
        return self.name

    def set_current_hp(self, hp: int):
        self.current_hp = max(0, min(hp, self.max_hp))

    def set_max_hp(self, max_hp: int):
        self.max_hp = max(0, max_hp)
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp

    def set_control_dict(self, control_dict: Dict[str, int]):
        self.control = control_dict.copy()

    def set_stealth(self, stlth: int):
        self.stealth = stlth

    # 状态检查
    def is_alive(self) -> bool:
        return self.current_hp > 0

    def is_full_health(self) -> bool:
        return self.current_hp >= self.max_hp

    def is_destroyed(self) -> bool:
        return self.current_hp <= 0

    def can_act(self) -> bool:
        return self.is_alive() and not self.is_controlled()

    def is_targetable(self) -> bool:
        """检查角色是否可被选为攻击目标（隐身角色不可被选）"""
        return self.is_alive() and self.stealth <= 0

    def on_turn_start(self):
        """基础回合开始逻辑：处理通用持续效果"""
        # 持续伤害：燃烧瓶每层3点，火阵每层2点
        burning_stacks = get_burning_block_stacks(self.block_id)
        if burning_stacks > 0:
            self.take_damage(3 * burning_stacks)
        if self.has_control("火阵"):
            self.take_damage(2 * self.get_control("火阵"))

    # 输出状态
    def display_status(self):
        print(f"=== {self.name} 状态 ===")
        print(f"生命值: {self.current_hp}/{self.max_hp}", end="")
        if self.is_destroyed():
            print(" [已摧毁]", end="")
        print()

        if self.is_controlled():
            print("状态: [被控制 - 下回合只能解控]", end="")
        else:
            print("状态: [正常]", end="")
        print()

        if self.control:
            print("控制效果: ", end="")
            for control_name, stacks in self.control.items():
                print(f"{control_name}({stacks}) ", end="")
            print()
        else:
            print("控制效果: 无")

        print(f"潜行: {self.stealth}")

        if self.skills:
            print("技能列表: ", end="")
            for name, skill in self.skills.items():
                print(f"{name}(CD:{skill.get_cooldown()}) ", end="")
            print()

        if self.accumulations:
            print("累积效果: ", end="")
            for effect, value in self.accumulations.items():
                print(f"{effect}({value}) ", end="")
            print()

        if self.imprints:
            print("印记: ", end="")
            for imprint, value in self.imprints.items():
                print(f"{imprint}({value}) ", end="")
            print()

        print(f"可行动: {'是' if self.can_act() else '否'}")

    # 特殊事件钩子
    def on_summon(self):
        print(f"{self.name} 被召唤到战场！")

    def on_destroy(self):
        print(f"{self.name} 从战场上消失！")
