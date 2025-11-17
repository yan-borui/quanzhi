# -*- coding: utf-8 -*-
# Summoner.py
from typing import Optional

from Behavior import BehaviorType
from Character import Character
from Skill import Skill


class Summoner(Character):
    def __init__(self, name: str = "召唤师"):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self._initialize_skills()

    def _initialize_skills(self):
        """初始化召唤师的技能"""
        # 狼
        wolf = Skill("狼", cooldown=1)
        wolf.set_effect(self._wolf_effect)
        self.add_or_replace_skill(wolf)

        # 熊
        bear = Skill("熊", cooldown=1)
        bear.set_effect(self._bear_effect)
        self.add_or_replace_skill(bear)

        # 齐攻
        coordinated_attack = Skill("齐攻", cooldown=1)
        coordinated_attack.set_effect(self._coordinated_attack_effect)
        self.add_or_replace_skill(coordinated_attack)

    def use_skill(self, skill_name: str):
        """使用技能（默认目标为自己）"""
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        """对目标使用技能"""
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return

        if not skill.is_available():
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return

        # 特殊技能条件检查
        if skill_name == "齐攻":
            wolf_accumulation = self.get_accumulation("狼")
            bear_accumulation = self.get_accumulation("熊")

            if wolf_accumulation < 4 and bear_accumulation < 4:
                print(f"齐攻需要至少4只狼或4只熊的积累！当前狼:{wolf_accumulation}, 熊:{bear_accumulation}")
                return

        # 执行技能
        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")

    def _wolf_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """狼效果：给自己加一个狼积累"""
        self.add_accumulation("狼", 1)
        print(f"{self.name} 召唤了一只狼，当前狼积累: {self.get_accumulation('狼')}")
        return True

    def _bear_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """熊效果：给自己加一个熊积累"""
        self.add_accumulation("熊", 1)
        print(f"{self.name} 召唤了一只熊，当前熊积累: {self.get_accumulation('熊')}")
        return True

    def _coordinated_attack_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """齐攻效果：消耗四只狼或者四只熊，造成30点伤害"""
        if not target:
            return False

        wolf_accumulation = self.get_accumulation("狼")
        bear_accumulation = self.get_accumulation("熊")

        # 检查并消耗积累
        if wolf_accumulation >= 4:
            self.reduce_accumulation("狼", 4)
            print(f"{self.name} 消耗了4只狼发动齐攻！")
        elif bear_accumulation >= 4:
            self.reduce_accumulation("熊", 4)
            print(f"{self.name} 消耗了4只熊发动齐攻！")
        else:
            print(f"齐攻失败：没有足够的狼或熊积累")
            return False

        # 造成伤害
        target.take_damage(30)
        return True

    def on_behavior_change(self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]):
        """行为改变时的回调"""
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 指挥召唤物向前推进！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 与召唤物一同后撤！")

    def reset_battle_round(self):
        """重置战斗回合状态（每局开始调用）"""
        # 清空所有积累
        self.accumulations.clear()
        print(f"{self.name} 准备就绪，所有召唤物积累已清空")


# 召唤师技能数据库
SUMMONER_SKILLS_DATA = {
    "狼": {
        "name": "狼",
        "cooldown": 0,
        "damage": 0,
        "effect": "增加1层狼积累",
        "range": "自身",
        "description": "召唤狼魂，积累狼群数量"
    },
    "熊": {
        "name": "熊",
        "cooldown": 0,
        "damage": 0,
        "effect": "增加1层熊积累",
        "range": "自身",
        "description": "召唤熊魂，积累熊群数量"
    },
    "齐攻": {
        "name": "齐攻",
        "cooldown": 0,
        "damage": 30,
        "effect": "消耗4只狼或4只熊发动强力攻击",
        "requirement": "需要至少4层狼积累或4层熊积累",
        "range": "任意敌方目标",
        "description": "指挥召唤物群体攻击，造成巨额伤害"
    }
}

# 召唤师属性数据库
SUMMONER_STATS_DATA = {
    "name": "召唤师",
    "max_hp": 60,
    "control": {},
    "stealth": 0,
    "role_type": "召唤系输出",
    "description": "通过积累召唤物数量来发动强力攻击的战术型角色"
}
