# -*- coding: utf-8 -*-
"""
ContinuousEffectSystem - 持续效果系统

管理持续多回合的效果，每回合自动触发。
效果可以被特定条件移除（例如移动可解除持续伤害）。
支持不同效果的叠加。

接口设计：
- 创建持续效果需要：名称、持续时间、每回合触发函数、移除条件
- 目标角色添加持续效果后，每回合自动处理
- 支持效果叠加和独立计时
"""

from typing import Callable, Optional, Any, List, Dict
from enum import Enum


class RemovalCondition(Enum):
    """移除条件枚举"""
    NEVER = "never"  # 永不移除（直到持续时间结束）
    ON_MOVEMENT = "on_movement"  # 移动时移除
    ON_DAMAGE = "on_damage"  # 受到伤害时移除
    ON_HEAL = "on_heal"  # 被治疗时移除
    ON_CONTROL = "on_control"  # 获得控制效果时移除
    CUSTOM = "custom"  # 自定义条件


class ContinuousEffect:
    """持续效果类"""
    
    def __init__(self, 
                 name: str,
                 duration: int,
                 trigger_func: Callable[[Any], None],
                 removal_condition: RemovalCondition = RemovalCondition.NEVER,
                 removal_check: Optional[Callable[[Any], bool]] = None,
                 source: Optional[Any] = None,
                 description: str = ""):
        """
        初始化持续效果
        
        Args:
            name: 效果名称
            duration: 持续回合数（-1表示永久）
            trigger_func: 每回合触发的函数，接受目标角色作为参数
            removal_condition: 移除条件类型
            removal_check: 自定义移除检查函数（当removal_condition为CUSTOM时使用）
            source: 效果来源（可选，通常是施法者）
            description: 效果描述
        """
        self.name = name
        self.duration = duration
        self.remaining_turns = duration
        self.trigger_func = trigger_func
        self.removal_condition = removal_condition
        self.removal_check = removal_check
        self.source = source
        self.description = description
        self.is_active = True
        
    def trigger(self, target: Any) -> bool:
        """
        触发效果
        
        Args:
            target: 目标角色
            
        Returns:
            bool: 是否成功触发
        """
        if not self.is_active:
            return False
        
        try:
            self.trigger_func(target)
            return True
        except Exception as e:
            print(f"[持续效果] {self.name} 触发失败: {e}")
            return False
    
    def decrease_duration(self) -> bool:
        """
        减少持续时间
        
        Returns:
            bool: 效果是否已结束
        """
        if self.remaining_turns > 0:
            self.remaining_turns -= 1
            
        return self.remaining_turns <= 0
    
    def check_removal_condition(self, target: Any, event: str) -> bool:
        """
        检查是否满足移除条件
        
        Args:
            target: 目标角色
            event: 事件类型 ("movement", "damage", "heal", "control")
            
        Returns:
            bool: 是否应该移除效果
        """
        if not self.is_active:
            return True
        
        # 检查预定义条件
        if self.removal_condition == RemovalCondition.ON_MOVEMENT and event == "movement":
            return True
        elif self.removal_condition == RemovalCondition.ON_DAMAGE and event == "damage":
            return True
        elif self.removal_condition == RemovalCondition.ON_HEAL and event == "heal":
            return True
        elif self.removal_condition == RemovalCondition.ON_CONTROL and event == "control":
            return True
        elif self.removal_condition == RemovalCondition.CUSTOM and self.removal_check:
            return self.removal_check(target)
        
        return False
    
    def deactivate(self):
        """停用效果"""
        self.is_active = False


class ContinuousEffectSystem:
    """持续效果管理系统"""
    
    def __init__(self):
        """初始化持续效果系统"""
        # 存储每个角色的持续效果列表: character_id -> List[ContinuousEffect]
        self.character_effects: Dict[int, List[ContinuousEffect]] = {}
    
    def add_effect(self, target: Any, effect: ContinuousEffect):
        """
        为目标添加持续效果
        
        Args:
            target: 目标角色
            effect: 持续效果对象
        """
        target_id = id(target)
        
        if target_id not in self.character_effects:
            self.character_effects[target_id] = []
        
        self.character_effects[target_id].append(effect)
        
        target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
        duration_str = f"{effect.duration}回合" if effect.duration > 0 else "永久"
        print(f"[持续效果] {target_name} 获得了 '{effect.name}' 效果 (持续: {duration_str})")
    
    def remove_effect(self, target: Any, effect_name: str) -> int:
        """
        移除目标的指定效果（移除所有同名效果）
        
        Args:
            target: 目标角色
            effect_name: 效果名称
            
        Returns:
            int: 移除的效果数量
        """
        target_id = id(target)
        
        if target_id not in self.character_effects:
            return 0
        
        effects = self.character_effects[target_id]
        removed_count = 0
        
        for effect in effects[:]:  # 使用副本进行迭代
            if effect.name == effect_name:
                effect.deactivate()
                effects.remove(effect)
                removed_count += 1
        
        if removed_count > 0:
            target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
            print(f"[持续效果] {target_name} 的 '{effect_name}' 效果被移除 (数量: {removed_count})")
        
        return removed_count
    
    def remove_single_effect(self, target: Any, effect_name: str) -> bool:
        """
        移除目标的指定效果（只移除一层）
        
        Args:
            target: 目标角色
            effect_name: 效果名称
            
        Returns:
            bool: 是否成功移除
        """
        target_id = id(target)
        
        if target_id not in self.character_effects:
            return False
        
        effects = self.character_effects[target_id]
        
        for effect in effects:
            if effect.name == effect_name:
                effect.deactivate()
                effects.remove(effect)
                
                target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
                print(f"[持续效果] {target_name} 的一层 '{effect_name}' 效果被移除")
                return True
        
        return False
    
    def clear_all_effects(self, target: Any):
        """
        清除目标的所有持续效果
        
        Args:
            target: 目标角色
        """
        target_id = id(target)
        
        if target_id in self.character_effects:
            effect_count = len(self.character_effects[target_id])
            if effect_count > 0:
                target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
                print(f"[持续效果] {target_name} 的所有持续效果被清除 (数量: {effect_count})")
            
            self.character_effects[target_id] = []
    
    def trigger_all_effects(self, target: Any):
        """
        触发目标的所有持续效果（通常在回合开始时调用）
        
        Args:
            target: 目标角色
        """
        target_id = id(target)
        
        if target_id not in self.character_effects:
            return
        
        effects = self.character_effects[target_id]
        
        if not effects:
            return
        
        target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
        print(f"\n[持续效果] 处理 {target_name} 的持续效果...")
        
        # 触发所有效果并减少持续时间
        effects_to_remove = []
        
        for effect in effects:
            if effect.is_active:
                print(f"  - 触发 '{effect.name}' (剩余 {effect.remaining_turns} 回合)")
                effect.trigger(target)
                
                # 减少持续时间
                if effect.decrease_duration():
                    effects_to_remove.append(effect)
                    print(f"    '{effect.name}' 效果已结束")
        
        # 移除已结束的效果
        for effect in effects_to_remove:
            effects.remove(effect)
    
    def check_and_remove_on_event(self, target: Any, event: str):
        """
        检查并移除满足条件的效果
        
        Args:
            target: 目标角色
            event: 事件类型 ("movement", "damage", "heal", "control")
        """
        target_id = id(target)
        
        if target_id not in self.character_effects:
            return
        
        effects = self.character_effects[target_id]
        effects_to_remove = []
        
        for effect in effects:
            if effect.check_removal_condition(target, event):
                effects_to_remove.append(effect)
        
        if effects_to_remove:
            target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
            for effect in effects_to_remove:
                effects.remove(effect)
                print(f"[持续效果] {target_name} 的 '{effect.name}' 因 {event} 被移除")
    
    def get_effects(self, target: Any) -> List[ContinuousEffect]:
        """
        获取目标的所有持续效果
        
        Args:
            target: 目标角色
            
        Returns:
            List[ContinuousEffect]: 效果列表
        """
        target_id = id(target)
        return self.character_effects.get(target_id, []).copy()
    
    def has_effect(self, target: Any, effect_name: str) -> bool:
        """
        检查目标是否有指定的持续效果
        
        Args:
            target: 目标角色
            effect_name: 效果名称
            
        Returns:
            bool: 是否有该效果
        """
        target_id = id(target)
        
        if target_id not in self.character_effects:
            return False
        
        return any(effect.name == effect_name for effect in self.character_effects[target_id])
    
    def get_effect_count(self, target: Any, effect_name: str) -> int:
        """
        获取目标的指定效果层数
        
        Args:
            target: 目标角色
            effect_name: 效果名称
            
        Returns:
            int: 效果层数
        """
        target_id = id(target)
        
        if target_id not in self.character_effects:
            return 0
        
        return sum(1 for effect in self.character_effects[target_id] if effect.name == effect_name)
