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
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Dict, Optional, List

# 添加Skill模块的导入路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from Skill import Skill
from Behavior import BehaviorType


class Character(ABC):
    def __init__(self, name: str = "", max_hp: int = 0, control: int = 0, stealth: int = 0):
        self.name = name
        self.max_hp = max(0, max_hp)
        self.current_hp = max(0, self.max_hp)
        self.control = control
        self.stealth = stealth

        self.skills: Dict[str, Skill] = {}
        self.imprints: Dict[str, int] = {}
        self.accumulations: Dict[str, int] = {}
        self.nearby_characters: List['Character'] = []
        self.current_behavior: Optional[BehaviorType] = None

    # 子类必须实现技能使用
    @abstractmethod
    def use_skill(self, skill_name: str):
        pass

    # 带目标的技能使用（可选实现）
    def use_skill_on_target(self, skill_name: str, target: 'Character'):
        # 默认实现忽略目标，子类可以重写
        self.use_skill(skill_name)

    def set_behavior(self, behavior: BehaviorType):
        """设置当前行为"""
        old_behavior = self.current_behavior
        self.current_behavior = behavior
        print(f"{self.name} 行为改变: {old_behavior} -> {behavior}")
        self.on_behavior_change(old_behavior, behavior)

    def get_behavior(self) -> Optional[BehaviorType]:
        """获取当前行为"""
        return self.current_behavior

    def on_behavior_change(self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]):
        """行为改变时的回调，子类可重写"""
        pass

    # 邻接表管理
    def add_nearby_character(self, character: 'Character'):
        """添加附近角色"""
        if character != self and character not in self.nearby_characters:
            self.nearby_characters.append(character)
            # 双向添加，确保双方都知道彼此在附近
            if self not in character.nearby_characters:
                character.add_nearby_character(self)
            print(f"{self.name} 与 {character.name} 距离变近")

    def remove_nearby_character(self, character: 'Character'):
        """移除附近角色"""
        if character in self.nearby_characters:
            self.nearby_characters.remove(character)
            # 双向移除
            if self in character.nearby_characters:
                character.remove_nearby_character(self)
            print(f"{self.name} 与 {character.name} 距离变远")

    def clear_nearby_characters(self):
        """清空附近角色列表"""
        for character in list(self.nearby_characters):
            self.remove_nearby_character(character)

    def get_nearby_characters(self) -> List['Character']:
        """获取附近角色列表"""
        return list(self.nearby_characters)

    def is_nearby(self, character: 'Character') -> bool:
        """检查是否在某个角色附近"""
        return character in self.nearby_characters

    # 受伤并显示（确保边界）
    def take_damage(self, damage: int):
        if damage <= 0:
            print(f"{self.name} 未受到有效伤害: {damage}")
            return

        was_alive = self.is_alive()  # 记录受伤前状态

        self.current_hp -= damage
        if self.current_hp < 0:
            self.current_hp = 0
        print(f"{self.name} 受到了 {damage} 点伤害，当前生命值: {self.current_hp}/{self.max_hp}")

        # 如果从存活状态变为摧毁状态，触发摧毁回调
        if was_alive and self.is_destroyed():
            self.on_destroy()

    # 治疗并显示
    def heal(self, amount: int):
        if amount <= 0:
            print(f"{self.name} 没有被有效治疗: {amount}")
            return
        self.current_hp += amount
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp
        print(f"{self.name} 恢复了 {amount} 点生命值，当前生命值: {self.current_hp}/{self.max_hp}")

    # 技能管理
    def has_skill(self, skill_name: str) -> bool:
        return skill_name in self.skills

    # 获取技能冷却（-1 表示不存在）
    def get_skill_cooldown(self, skill_name: str) -> int:
        if skill_name in self.skills:
            return self.skills[skill_name].get_cooldown()
        return -1

    # 设置技能冷却（如果技能存在）
    def set_skill_cooldown(self, skill_name: str, cooldown: int):
        if skill_name in self.skills:
            self.skills[skill_name].set_cooldown(cooldown)

    # 将所有技能冷却-1（不小于0）
    def reduce_all_cooldowns(self):
        for skill in self.skills.values():
            skill.reduce_cooldown()

    # 添加或替换技能
    def add_or_replace_skill(self, skill: Skill):
        if not skill.get_name():
            return
        self.skills[skill.get_name()] = skill

    # 添加或替换技能（复制版本）
    def add_or_replace_skill_copy(self, skill: Skill):
        if not skill.get_name():
            return
        self.skills[skill.get_name()] = Skill(skill.get_name(), skill.get_base_cooldown())

    # 获取技能引用（更安全的访问方式）
    def get_skill(self, skill_name: str) -> Optional[Skill]:
        return self.skills.get(skill_name)

    # 印记管理（get/set/remove/clear）
    def add_imprint(self, imprint: str, value: int):
        if not imprint:
            return
        self.imprints[imprint] = value
        print(f"{self.name} 获得了 {imprint} 印记，值: {value}")

    def get_imprint(self, imprint: str) -> int:
        return self.imprints.get(imprint, 0)

    # 安全地减少一层印记（不会变为负数）
    def remove_imprint(self, imprint: str):
        if imprint not in self.imprints:
            print(f"{self.name} 不存在印记: {imprint}")
            return

        if self.imprints[imprint] > 1:
            self.imprints[imprint] -= 1
            print(f"{self.name} 移除了一层 {imprint} 印记，剩余: {self.imprints[imprint]}")
        else:
            del self.imprints[imprint]
            print(f"{self.name} 清除了 {imprint} 印记")

    def clear_imprint(self, imprint: str):
        if imprint in self.imprints:
            del self.imprints[imprint]
            print(f"{self.name} 清除了 {imprint} 累积效果")

    # 累积效果管理（与 Player 的 accumulations 功能一致）
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
            print(f"{self.name} 消耗了 {effect} 累积效果，剩余: {self.accumulations[effect]}")

    def clear_accumulation(self, effect: str):
        if effect in self.accumulations:
            del self.accumulations[effect]
            print(f"{self.name} 清除了 {effect} 累积效果")

    # 属性访问与设置（带边界检查）
    def get_current_hp(self) -> int:
        return self.current_hp

    def get_max_hp(self) -> int:
        return self.max_hp

    def get_control(self) -> int:
        return self.control

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

    def set_control(self, ctrl: int):
        self.control = ctrl

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
        return self.is_alive() and self.control == 0

    # 输出状态
    def display_status(self):
        print(f"=== {self.name} 状态 ===")
        print(f"生命值: {self.current_hp}/{self.max_hp}", end="")
        if self.is_destroyed():
            print(" [已摧毁]", end="")
        print()
        print(f"控制: {self.control}")
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

    # 特殊事件钩子，子类可重写
    def on_summon(self):
        print(f"{self.name} 被召唤到战场！")

    def on_destroy(self):
        print(f"{self.name} 从战场上消失！")
