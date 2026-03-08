# -*- coding: utf-8 -*-
# scientist.py - 科学家
"""
科学家角色实现

技能表：
- 高压电池 (CD:2) — 12伤害 + 控制
- 燃烧电池 (CD:1) — 6伤害
- 电池 (CD:0) — 电池+1
- 制造机器人 (CD:0) — 消耗4个电池，机器人+1
- 撸 (CD:0) — 伤害为 n/20（60HP基准），n为机器人数量
- 机器人自爆 (CD:0) — 伤害为 n/4（60HP基准），消耗所有n个机器人

关键机制：
- 电池和机器人都是资源，使用 accumulation 系统管理
- 制造机器人需要消耗4个电池
- 撸和机器人自爆的伤害随机器人数量增长
- 死后转移到机器人上（如果有机器人），只能使用撸或机器人自爆
- 机器人模式下没有机器人后真正死亡
"""

from typing import Optional, List

from core.behavior import BehaviorType
from core.character import Character
from core.skill import Skill


class MiniRobot(Character):
    """科学家制造的小机器人 — 可被其他角色选中为目标，不参与石头剪刀布"""

    is_mini_robot = True

    def __init__(self, name: str, owner: "Scientist"):
        super().__init__(name, max_hp=1, control={}, stealth=0)
        self._owner = owner

    def use_skill(self, skill_name: str):
        pass

    def on_destroy(self):
        print(f"机器人 {self.name} 被摧毁！")


class Scientist(Character):
    def __init__(self, name: str = "科学家"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()
        # 是否处于机器人模式（死后转移到机器人上）
        self._in_robot_mode = False
        # 命名小机器人列表
        self._named_robots: List[MiniRobot] = []
        # 制造机器人前由外部（CLI/后端）设置的名字
        self._pending_robot_name: Optional[str] = None

    def _initialize_skills(self):
        high_voltage = Skill("高压电池", cooldown=2)
        high_voltage.set_effect(self._high_voltage_effect)
        self.add_or_replace_skill(high_voltage)

        burning = Skill("燃烧电池", cooldown=1)
        burning.set_effect(self._burning_effect)
        self.add_or_replace_skill(burning)

        battery = Skill("电池", cooldown=0)
        battery.set_effect(self._battery_effect)
        self.add_or_replace_skill(battery)

        build_robot = Skill("制造机器人", cooldown=0)
        build_robot.set_effect(self._build_robot_effect)
        self.add_or_replace_skill(build_robot)

        punch = Skill("撸", cooldown=0)
        punch.set_effect(self._punch_effect)
        self.add_or_replace_skill(punch)

        self_destruct = Skill("机器人自爆", cooldown=0)
        self_destruct.set_effect(self._self_destruct_effect)
        self.add_or_replace_skill(self_destruct)

    @property
    def battery_count(self) -> int:
        """当前电池数量"""
        return self.get_accumulation("电池")

    @property
    def robot_count(self) -> int:
        """当前存活机器人数量（基于命名机器人列表）"""
        return sum(1 for r in self._named_robots if r.is_alive())

    def set_pending_robot_name(self, name: str):
        """制造机器人前由CLI/后端调用，设置即将建造的机器人名字"""
        self._pending_robot_name = name

    def get_named_robots(self) -> List[MiniRobot]:
        """返回所有命名机器人（含已死亡）"""
        return list(self._named_robots)

    @property
    def in_robot_mode(self) -> bool:
        """是否处于机器人模式"""
        return self._in_robot_mode

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

        # 机器人模式下只能使用撸和机器人自爆
        if self._in_robot_mode:
            if skill_name not in ("撸", "机器人自爆"):
                print(f"{self.name} 处于机器人模式，只能使用撸或机器人自爆！")
                return

        # 制造机器人需要至少4个电池
        if skill_name == "制造机器人":
            if self.battery_count < 4:
                print(f"制造机器人需要至少4个电池！当前电池: {self.battery_count}")
                return

        # 撸需要至少1个机器人
        if skill_name == "撸":
            if self.robot_count < 1:
                print(f"撸需要至少1个机器人！当前机器人: {self.robot_count}")
                return

        # 机器人自爆需要至少1个机器人
        if skill_name == "机器人自爆":
            if self.robot_count < 1:
                print(f"机器人自爆需要至少1个机器人！当前机器人: {self.robot_count}")
                return

        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    # --- 技能效果函数 ---

    def _high_voltage_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """高压电池：12点伤害 + 控制"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(12))
        target.add_control("高压电池", 1)
        print(f"{target.get_name()} 被高压电池击中，陷入麻痹！")
        return True

    def _burning_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """燃烧电池：6点伤害"""
        if not target:
            return False
        target.take_damage(self.apply_attack_buff(6))
        return True

    def _battery_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """电池：电池+1"""
        self.add_accumulation("电池", 1)
        print(f"{self.name} 制造了1个电池，当前电池: {self.battery_count}")
        return True

    def _build_robot_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """制造机器人：消耗4个电池，创建一个命名小机器人"""
        # 消耗4个电池
        self.reduce_accumulation("电池", 4)
        print(f"{self.name} 消耗了4个电池，剩余电池: {self.battery_count}")

        # 使用预设名称或自动生成名称
        name = self._pending_robot_name or f"机器人{len(self._named_robots) + 1}"
        self._pending_robot_name = None
        robot = MiniRobot(name, owner=self)
        self._named_robots.append(robot)
        print(
            f"{self.name} 制造了小机器人 [{robot.name}]！当前机器人: {self.robot_count}"
        )
        return True

    def _punch_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """
        撸：伤害与机器人数量成正比。
        ATK/60 = n/20，基于 60 HP 标准：伤害 = 3 * n
        """
        if not target:
            return False
        n = self.robot_count
        damage = 3 * n
        print(f"{self.name} 操控 {n} 个机器人撸击！伤害: {damage}")
        target.take_damage(self.apply_attack_buff(damage))
        return True

    def _self_destruct_effect(
        self, caster: Character, target: Optional[Character]
    ) -> bool:
        """
        机器人自爆：消耗所有机器人，伤害与数量成正比。
        ATK/60 = n/4，基于 60 HP 标准：伤害 = 15 * n
        """
        if not target:
            return False
        n = self.robot_count
        damage = 15 * n
        print(f"{self.name} 引爆了 {n} 个机器人自爆！伤害: {damage}")
        # 摧毁所有命名机器人
        for robot in self._named_robots:
            if robot.is_alive():
                robot.current_hp = 0
                print(f"机器人 {robot.name} 在自爆中被摧毁！")
        target.take_damage(self.apply_attack_buff(damage))

        # 如果在机器人模式下自爆后没有机器人了，真正死亡
        if self._in_robot_mode and self.robot_count <= 0:
            print(f"{self.name} 的最后一批机器人自爆了，科学家真正阵亡！")
            self._in_robot_mode = False
            self.current_hp = 0
            super().on_destroy()

        return True

    def on_destroy(self):
        """
        科学家死亡时触发：
        如果有机器人，转移到机器人上只能使用撸或机器人自爆。
        """
        if self.robot_count > 0 and not self._in_robot_mode:
            self._in_robot_mode = True
            # 复活到机器人上，以1HP存活（标记状态）
            self.current_hp = 1
            self.max_hp = 1
            print(
                f"{self.name} 死亡！但转移到了机器人上！"
                f"当前机器人: {self.robot_count}，只能使用撸或机器人自爆！"
            )
        else:
            self._in_robot_mode = False
            super().on_destroy()

    def is_alive(self) -> bool:
        """科学家在机器人模式下仍然存活"""
        if self._in_robot_mode and self.robot_count > 0:
            return True
        return super().is_alive()

    def take_damage(self, damage: int):
        """
        科学家在机器人模式下受伤时，损失一个命名机器人而非生命值。
        """
        if self._in_robot_mode and self.robot_count > 0:
            # 单次护盾效果
            if self.has_control("护盾"):
                self.clear_control("护盾")
                print(f"{self.name} 的护盾抵消了这次攻击！")
                return

            # 摧毁第一个存活的命名机器人
            for robot in self._named_robots:
                if robot.is_alive():
                    robot.current_hp = 0
                    print(
                        f"{self.name}（机器人模式）受到攻击，机器人 [{robot.name}] 被摧毁！"
                        f"剩余机器人: {self.robot_count}"
                    )
                    break
            if self.robot_count <= 0:
                print(f"{self.name} 的所有机器人被摧毁，科学家真正阵亡！")
                self._in_robot_mode = False
                self.current_hp = 0
                super().on_destroy()
        else:
            super().take_damage(damage)

    def on_behavior_change(
        self,
        old_behavior: Optional[BehaviorType],
        new_behavior: Optional[BehaviorType],
    ):
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 操控机器人向前推进！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 启动反重力装置后撤！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 用电磁脉冲挣脱束缚！")

    def reset_battle_round(self):
        """新一局重置：清除电池和所有命名机器人"""
        self.clear_accumulation("电池")
        for robot in self._named_robots:
            robot.current_hp = 0
        self._named_robots.clear()
        self._pending_robot_name = None
        self._in_robot_mode = False
        print(f"{self.name} 准备就绪，所有状态已重置")

    def display_status(self):
        """显示科学家状态，额外显示机器人模式信息"""
        super().display_status()
        if self._in_robot_mode:
            print(
                f"[机器人模式] 机器人数量: {self.robot_count}，只能使用撸或机器人自爆"
            )


SCIENTIST_SKILLS_DATA = {
    "高压电池": {
        "name": "高压电池",
        "cooldown": 2,
        "damage": 12,
        "effect": "控制",
        "common": True,
        "special": "死后转移到机器人上，只能撸或自爆",
    },
    "燃烧电池": {
        "name": "燃烧电池",
        "cooldown": 1,
        "damage": 6,
        "effect": "无",
    },
    "电池": {
        "name": "电池",
        "cooldown": 0,
        "damage": 0,
        "effect": "电池+1",
    },
    "制造机器人": {
        "name": "制造机器人",
        "cooldown": 0,
        "damage": 0,
        "effect": "消耗4个电池，机器人+1",
        "requirement": "需要至少4个电池",
    },
    "撸": {
        "name": "撸",
        "cooldown": 0,
        "damage": "3*n (n=机器人数)",
        "effect": "无",
        "requirement": "需要至少1个机器人",
    },
    "机器人自爆": {
        "name": "机器人自爆",
        "cooldown": 0,
        "damage": "15*n (n=机器人数)",
        "effect": "消耗所有机器人",
        "requirement": "需要至少1个机器人",
    },
}

SCIENTIST_STATS_DATA = {
    "name": "科学家",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "资源/机械",
    "description": "通过积累电池制造机器人的角色，死后可转移到机器人上继续战斗",
}
