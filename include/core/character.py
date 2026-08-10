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

from core.event_log import emit
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional, List
from core.skill import Skill
from core.behavior import BehaviorType
from core.damage import DamageEvent
from core.status_effects import (
    NON_BLOCKING_CONTROL_NAMES,
    accumulation_bucket,
    control_blocks_action,
    control_is_non_blocking,
)

HARMLESS_CONTROLS = set(NON_BLOCKING_CONTROL_NAMES)


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
        self._block_move_handler: Optional[Callable[["Character", int], bool]] = None

        self.skills: Dict[str, Skill] = {}
        self.imprints: Dict[str, int] = {}
        self.resources: Dict[str, int] = {}
        self.modifiers: Dict[str, int] = {}
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

    def set_block_id(self, block_id: int) -> None:
        """设置角色所在的块ID。

        角色进入对局后，由地块状态的写入 Module 同步派生缓存；
        未进入对局的独立角色保留原有直接设置行为。
        """
        if self._block_move_handler is None:
            self.block_id = block_id
            return
        self._block_move_handler(self, block_id)

    def _bind_block_move_handler(
        self,
        handler: Optional[Callable[["Character", int], bool]],
    ) -> None:
        """绑定对局内的地块写入函数。"""
        self._block_move_handler = handler

    def _set_block_id_from_battle(self, block_id: int) -> None:
        """由地块状态 Module 执行的底层写入。"""
        self.block_id = block_id

    def is_controlled(self) -> bool:
        """检查角色是否被控制（有控制效果）"""
        return any(control_blocks_action(k) for k in self.control.keys())

    def get_blocking_controls(self) -> List[str]:
        return [
            control_name
            for control_name in self.control.keys()
            if control_blocks_action(control_name)
        ]

    def get_non_blocking_controls(self) -> List[str]:
        return [
            control_name
            for control_name in self.control.keys()
            if control_is_non_blocking(control_name)
        ]

    def format_skill_action(
        self, skill_name: str, skill: Skill, reason: str = ""
    ) -> str:
        if reason:
            return f"技能:{skill_name}({reason})"
        if skill.is_available():
            return f"技能:{skill_name}"
        return f"技能:{skill_name}(CD:{skill.get_cooldown()})"

    def describe_skill_action(self, skill_name: str, skill: Skill, battle) -> str:
        return self.format_skill_action(skill_name, skill)

    def available_when_controlled_actions(self, battle) -> List[str]:
        return []

    def available_when_defeated_actions(self, battle) -> List[str]:
        return []

    # 带目标的技能使用（可选实现）
    def use_skill_on_target(self, skill_name: str, target: "Character"):
        # 默认实现忽略目标，子类可以重写
        self.use_skill(skill_name)

    def execute_skill_action(
        self,
        skill_name: str,
        target: "Character",
        validator: Optional[Callable[[], Optional[str]]] = None,
    ) -> bool:
        """统一技能施放管线；角色只提供额外验证与效果 Implementation。"""
        skill = self.get_skill(skill_name)
        if not skill:
            emit(f"{self.name} 没有技能: {skill_name}")
            return False
        if not skill.is_available():
            emit(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return False
        if validator is not None:
            error = validator()
            if error:
                emit(error)
                return False
        success = skill.execute_with_target(self, target)
        if success:
            emit(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")
        return success

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
            emit(f"{self.name} 与 {character.name} 距离变近")

    def remove_nearby_character(self, character: "Character"):
        """移除附近角色"""
        if character in self.nearby_characters:
            self.nearby_characters.remove(character)
            if self in character.nearby_characters:
                character.remove_nearby_character(self)
            emit(f"{self.name} 与 {character.name} 距离变远")

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
        buff = self.get_modifier("攻击强化")
        if buff > 0:
            emit(f"{self.name} 的攻击强化效果生效，伤害增加 {buff} 点")
            self.clear_modifier("攻击强化")
            return base_damage + buff
        return base_damage

    def absorb_damage_with_shield(self, damage: int) -> bool:
        """结算通用护盾/立盾；返回本次伤害是否已被完全承担。"""
        if self.has_control("护盾"):
            self.clear_control("护盾")
            emit(f"{self.name} 的护盾抵消了这次攻击！")
            return True

        shield_hp = self.get_modifier("立盾")
        if shield_hp <= 0:
            return False

        self.reduce_modifier("立盾", damage)
        remaining_shield = self.get_modifier("立盾")
        if remaining_shield > 0:
            emit(
                f"{self.name} 的立盾承受了 {damage} 点伤害，"
                f"立盾剩余血量: {remaining_shield}"
            )
        else:
            emit(f"{self.name} 的立盾被打破！")
        return True

    def take_damage(self, damage: int):
        """旧调用方兼容 Adapter。"""
        return self.receive_damage(DamageEvent(amount=damage))

    def intercept_damage(self, event: DamageEvent) -> bool:
        """角色形态可在此完整接管伤害；True 表示结算结束。"""
        return False

    def before_damage(self, event: DamageEvent):
        """在任何护盾或形态拦截前执行的伤害通知 hook。"""

    def after_damage(self, event: DamageEvent, was_alive: bool):
        """生命伤害完成后的通知 hook。"""

    def modify_incoming_damage(self, event: DamageEvent) -> int:
        """角色特有减伤/增伤 hook。"""
        return event.amount

    def receive_damage(self, event: DamageEvent):
        """统一伤害结算管线。"""
        damage = event.amount
        if damage <= 0:
            emit(f"{self.name} 未受到有效伤害: {damage}")
            return

        self.before_damage(event)
        if self.intercept_damage(event):
            return

        damage = self.modify_incoming_damage(event)
        if self.absorb_damage_with_shield(damage):
            return

        # 易伤效果：受到伤害增加，然后消耗易伤
        vulnerability = self.get_modifier("易伤")
        if vulnerability > 0:
            bonus = damage * vulnerability // 100
            damage += bonus
            emit(f"{self.name} 的易伤效果生效，伤害增加 {bonus} 点")
            self.clear_modifier("易伤")

        was_alive = self.is_alive()
        self.current_hp -= damage
        if self.current_hp < 0:
            self.current_hp = 0

        # 记录本回合受到的伤害
        self._current_turn_log()["damage"] += damage

        emit(
            f"{self.name} 受到了 {damage} 点伤害，当前生命值: {self.current_hp}/{self.max_hp}"
        )

        if was_alive and self.is_destroyed():
            self.prepare_for_death()
            self.on_destroy()
        self.after_damage(event, was_alive)

    # 治疗并显示
    def heal(self, amount: int):
        if amount <= 0:
            emit(f"{self.name} 没有被有效治疗: {amount}")
            return
        self.current_hp += amount
        if self.current_hp > self.max_hp:
            self.current_hp = self.max_hp

        # 记录本回合治疗
        self._current_turn_log()["heal"] += amount

        emit(
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

        emit(
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
            emit(f"{self.name} 没有控制效果: {control_name}")
            return

        removed = min(stacks, self.control[control_name])
        self.control[control_name] -= stacks
        if self.control[control_name] <= 0:
            del self.control[control_name]
            emit(f"{self.name} 清除了 {control_name} 控制效果")
        else:
            emit(
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
            emit(f"{self.name} 清除了 {control_name} 控制效果")

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

        emit(
            f"{self.name} 获得了 {imprint} 印记，值: {value}，当前值: {self.imprints[imprint]}"
        )

    def get_imprint(self, imprint: str) -> int:
        return self.imprints.get(imprint, 0)

    def remove_imprint(self, imprint: str):
        if imprint not in self.imprints:
            emit(f"{self.name} 不存在印记: {imprint}")
            return

        if self.imprints[imprint] > 1:
            self.imprints[imprint] -= 1
            emit(
                f"{self.name} 移除了一层 {imprint} 印记，剩余: {self.imprints[imprint]}"
            )
        else:
            del self.imprints[imprint]
            emit(f"{self.name} 清除了 {imprint} 印记")

    def clear_imprint(self, imprint: str):
        if imprint in self.imprints:
            del self.imprints[imprint]
            emit(f"{self.name} 清除了 {imprint} 累积效果")

    # 累积效果管理
    @property
    def accumulations(self) -> Dict[str, int]:
        return {**self.resources, **self.modifiers}

    @accumulations.setter
    def accumulations(self, values: Dict[str, int]):
        self.resources = {}
        self.modifiers = {}
        for effect, value in values.items():
            if accumulation_bucket(effect) == "modifier":
                self.modifiers[effect] = value
            else:
                self.resources[effect] = value

    def _accumulation_store(self, effect: str) -> Dict[str, int]:
        if accumulation_bucket(effect) == "modifier":
            return self.modifiers
        return self.resources

    def add_resource(self, resource: str, value: int):
        self._add_accumulation_to(self.resources, resource, value, "资源")

    def get_resource(self, resource: str) -> int:
        return self.resources.get(resource, 0)

    def reduce_resource(self, resource: str, number: int):
        self._reduce_accumulation_from(self.resources, resource, number, "资源")

    def clear_resource(self, resource: str):
        self._clear_accumulation_from(self.resources, resource, "资源")

    def add_modifier(self, modifier: str, value: int):
        self._add_accumulation_to(self.modifiers, modifier, value, "战斗修正")

    def get_modifier(self, modifier: str) -> int:
        return self.modifiers.get(modifier, 0)

    def reduce_modifier(self, modifier: str, number: int):
        self._reduce_accumulation_from(self.modifiers, modifier, number, "战斗修正")

    def clear_modifier(self, modifier: str):
        self._clear_accumulation_from(self.modifiers, modifier, "战斗修正")

    def clear_accumulations(self):
        self.resources.clear()
        self.modifiers.clear()

    def add_accumulation(self, effect: str, value: int):
        self._add_accumulation_to(
            self._accumulation_store(effect), effect, value, "累积效果"
        )

    def get_accumulation(self, effect: str) -> int:
        return self.resources.get(effect, self.modifiers.get(effect, 0))

    def reduce_accumulation(self, effect: str, number: int):
        self._reduce_accumulation_from(
            self._accumulation_store(effect), effect, number, "累积效果"
        )

    def clear_accumulation(self, effect: str):
        self._clear_accumulation_from(
            self._accumulation_store(effect), effect, "累积效果"
        )

    def _add_accumulation_to(
        self, store: Dict[str, int], effect: str, value: int, label: str
    ):
        if not effect:
            return
        store[effect] = store.get(effect, 0) + value
        emit(f"{self.name} 获得了 {effect} {label}，值: {store[effect]}")

    def _reduce_accumulation_from(
        self, store: Dict[str, int], effect: str, number: int, label: str
    ):
        if effect not in store:
            emit(f"{self.name} 没有{label}: {effect}")
            return

        store[effect] -= number
        if store[effect] <= 0:
            del store[effect]
            emit(f"{self.name} 消耗并清除了 {effect} {label}")
        else:
            emit(f"{self.name} 消耗了 {effect} {label}，剩余: {store[effect]}")

    def _clear_accumulation_from(self, store: Dict[str, int], effect: str, label: str):
        if effect in store:
            del store[effect]
            emit(f"{self.name} 清除了 {effect} {label}")

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
        """基础回合开始逻辑：处理角色自身状态造成的回合伤害。"""
        # 地块类持续效果由 ContinuousEffectSystem 处理。
        if self.has_control("火阵"):
            self.take_damage(2 * self.get_control("火阵"))

    # 输出状态
    def display_status(self):
        emit(f"=== {self.name} 状态 ===")
        emit(f"生命值: {self.current_hp}/{self.max_hp}", end="")
        if self.is_destroyed():
            emit(" [已摧毁]", end="")
        emit()

        if self.is_controlled():
            emit("状态: [被控制 - 下回合只能解控]", end="")
        else:
            emit("状态: [正常]", end="")
        emit()

        if self.control:
            emit("控制效果: ", end="")
            for control_name, stacks in self.control.items():
                emit(f"{control_name}({stacks}) ", end="")
            emit()
        else:
            emit("控制效果: 无")

        emit(f"潜行: {self.stealth}")

        if self.skills:
            emit("技能列表: ", end="")
            for name, skill in self.skills.items():
                emit(f"{name}(CD:{skill.get_cooldown()}) ", end="")
            emit()

        if self.resources:
            emit("资源: ", end="")
            for effect, value in self.resources.items():
                emit(f"{effect}({value}) ", end="")
            emit()

        if self.modifiers:
            emit("战斗修正: ", end="")
            for effect, value in self.modifiers.items():
                emit(f"{effect}({value}) ", end="")
            emit()

        if self.imprints:
            emit("印记: ", end="")
            for imprint, value in self.imprints.items():
                emit(f"{imprint}({value}) ", end="")
            emit()

        emit(f"可行动: {'是' if self.can_act() else '否'}")

    # 特殊事件钩子
    def on_summon(self):
        emit(f"{self.name} 被召唤到战场！")

    def prepare_for_death(self):
        """统一死亡前清理，供伤害和直接死亡路径复用。"""
        if self.control:
            emit(f"{self.name} 死亡时清除了所有控制效果")
            self.clear_all_controls()

    def on_destroy(self):
        self.prepare_for_death()
        emit(f"{self.name} 从战场上消失！")
