# -*- coding: utf-8 -*-
# 示例新角色：法师 (Mage)
# 这是一个示例角色，展示如何扩展游戏系统

from typing import Optional
from Behavior import BehaviorType
from Character import Character
from Skill import Skill


class Mage(Character):
    """法师 - 魔法输出型角色"""
    
    def __init__(self, name: str = "法师"):
        super().__init__(name, max_hp=45, control={}, stealth=0)
        self._initialize_skills()
        self.mana = 100  # 法力值
        self.max_mana = 100
    
    def _initialize_skills(self):
        """初始化法师技能"""
        # 技能1：火球术 - 基础攻击
        fireball = Skill("火球术", cooldown=0)
        fireball.set_effect(self._fireball_effect)
        self.add_or_replace_skill(fireball)
        
        # 技能2：冰冻术 - 控制技能
        freeze = Skill("冰冻术", cooldown=2)
        freeze.set_effect(self._freeze_effect)
        self.add_or_replace_skill(freeze)
        
        # 技能3：魔法护盾 - 防御技能
        shield = Skill("魔法护盾", cooldown=3)
        shield.set_effect(self._magic_shield_effect)
        self.add_or_replace_skill(shield)
    
    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)
    
    def use_skill_on_target(self, skill_name: str, target: Character):
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return
        
        # 检查法力值
        mana_cost = self._get_mana_cost(skill_name)
        if self.mana < mana_cost:
            print(f"法力值不足！需要 {mana_cost}，当前 {self.mana}")
            return
        
        if not skill.is_available():
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return
        
        success = skill.execute_with_target(self, target)
        if success:
            self.mana -= mana_cost
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}，消耗 {mana_cost} 法力 (剩余: {self.mana})")
    
    def _get_mana_cost(self, skill_name: str) -> int:
        """获取技能法力消耗"""
        costs = {
            "火球术": 20,
            "冰冻术": 40,
            "魔法护盾": 30
        }
        return costs.get(skill_name, 0)
    
    def _fireball_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """火球术：造成中等伤害"""
        if not target:
            return False
        target.take_damage(8)
        return True
    
    def _freeze_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """冰冻术：造成伤害并冰冻目标"""
        if not target:
            return False
        target.take_damage(5)
        target.add_control("冰冻", 1)
        return True
    
    def _magic_shield_effect(self, caster: Character, target: Optional[Character]) -> bool:
        """魔法护盾：为自己添加护盾印记"""
        caster.add_imprint("魔法护盾", 3)
        print(f"{caster.name} 获得了3层魔法护盾，可以抵消伤害")
        return True
    
    def take_damage(self, damage: int):
        """重写受伤逻辑，护盾可以抵消伤害"""
        shield_stacks = self.get_imprint("魔法护盾")
        if shield_stacks > 0:
            # 护盾抵消伤害
            blocked = min(damage, shield_stacks * 5)  # 每层护盾抵消5点伤害
            actual_damage = damage - blocked
            
            # 消耗护盾层数
            consumed_stacks = (blocked + 4) // 5  # 向上取整
            for _ in range(consumed_stacks):
                if self.get_imprint("魔法护盾") > 0:
                    self.remove_imprint("魔法护盾")
            
            print(f"{self.name} 的魔法护盾抵消了 {blocked} 点伤害")
            
            if actual_damage > 0:
                super().take_damage(actual_damage)
        else:
            super().take_damage(damage)
    
    def on_turn_start(self):
        """每回合开始恢复法力"""
        super().on_turn_start()
        if self.mana < self.max_mana:
            mana_regen = 15
            self.mana = min(self.max_mana, self.mana + mana_regen)
            print(f"{self.name} 恢复了 {mana_regen} 法力值，当前: {self.mana}/{self.max_mana}")
    
    def on_behavior_change(self, old_behavior: Optional[BehaviorType], new_behavior: Optional[BehaviorType]):
        """行为改变时的提示"""
        if new_behavior == BehaviorType.MOVE_CLOSE:
            print(f"{self.name} 飘浮前进，准备近距离施法！")
        elif new_behavior == BehaviorType.MOVE_AWAY:
            print(f"{self.name} 瞬移远离，保持安全距离！")
        elif new_behavior == BehaviorType.REMOVE_CONTROL:
            print(f"{self.name} 念诵咒语解除控制！")
    
    def reset_battle_round(self):
        """重置战斗状态"""
        self.mana = self.max_mana
        print(f"{self.name} 准备就绪，法力值已充满")


# 技能数据
MAGE_SKILLS_DATA = {
    "火球术": {
        "name": "火球术",
        "cooldown": 0,
        "damage": 8,
        "mana_cost": 20,
        "effect": "发射火球造成伤害",
        "range": "远程"
    },
    "冰冻术": {
        "name": "冰冻术",
        "cooldown": 2,
        "damage": 5,
        "mana_cost": 40,
        "effect": "造成伤害并冰冻目标1回合",
        "range": "远程"
    },
    "魔法护盾": {
        "name": "魔法护盾",
        "cooldown": 3,
        "damage": 0,
        "mana_cost": 30,
        "effect": "为自己添加3层护盾，每层抵消5点伤害",
        "range": "自身"
    }
}

# 角色数据
MAGE_STATS_DATA = {
    "name": "法师",
    "max_hp": 45,
    "max_mana": 100,
    "control": {},
    "stealth": 0,
    "role_type": "魔法输出",
    "description": "使用魔法进行远程攻击和控制的脆皮角色"
}
