# -*- coding: utf-8 -*-
"""
DualJudgmentSystem - 双人石头剪刀布判定系统

用于处理技能发起方与承受方之间的石头剪刀布判定。
部分技能可以要求双方进行判定，赢的一方获得技能成功或失败的结果。
某些技能可以修改判定规则，例如让发起方直接获胜。

接口设计：
- 提供发起方、承受方和技能名作为参数
- 返回判定赢家
- 支持自定义判定规则（如自动获胜）
"""

import random
from typing import Optional, Callable, Any
from enum import Enum


class JudgmentResult(Enum):
    """判定结果枚举"""
    INITIATOR_WIN = "initiator_win"  # 发起方获胜
    TARGET_WIN = "target_win"  # 承受方获胜
    DRAW = "draw"  # 平局


class DualJudgmentSystem:
    """双人石头剪刀布判定系统"""
    
    def __init__(self):
        """初始化判定系统"""
        self.choices = ['石头', '剪刀', '布']
        # 存储技能特殊规则: skill_name -> rule_function
        # rule_function(initiator, target) -> Optional[JudgmentResult]
        # 返回None表示使用正常判定，返回结果表示强制结果
        self.skill_rules: dict[str, Callable[[Any, Any], Optional[JudgmentResult]]] = {}
        
    def register_skill_rule(self, skill_name: str, 
                           rule_func: Callable[[Any, Any], Optional[JudgmentResult]]):
        """
        注册技能的特殊判定规则
        
        Args:
            skill_name: 技能名称
            rule_func: 规则函数，接受(发起方, 承受方)，返回Optional[JudgmentResult]
                      返回None表示使用正常RPS判定
                      返回JudgmentResult表示强制判定结果
        """
        self.skill_rules[skill_name] = rule_func
        print(f"[判定系统] 为技能 '{skill_name}' 注册了特殊规则")
    
    def unregister_skill_rule(self, skill_name: str):
        """取消注册技能的特殊判定规则"""
        if skill_name in self.skill_rules:
            del self.skill_rules[skill_name]
            print(f"[判定系统] 移除了技能 '{skill_name}' 的特殊规则")
    
    def judge(self, initiator: Any, target: Any, skill_name: str = "") -> JudgmentResult:
        """
        执行双人判定
        
        Args:
            initiator: 发起方（角色对象）
            target: 承受方（角色对象）
            skill_name: 技能名称（可选，用于应用特殊规则）
            
        Returns:
            JudgmentResult: 判定结果
        """
        # 检查是否有特殊规则
        if skill_name and skill_name in self.skill_rules:
            forced_result = self.skill_rules[skill_name](initiator, target)
            if forced_result is not None:
                print(f"[判定系统] 技能 '{skill_name}' 应用特殊规则，结果: {forced_result.value}")
                return forced_result
        
        # 正常石头剪刀布判定
        return self._normal_rps_judgment(initiator, target, skill_name)
    
    def _normal_rps_judgment(self, initiator: Any, target: Any, skill_name: str = "") -> JudgmentResult:
        """
        执行正常的石头剪刀布判定
        
        Args:
            initiator: 发起方
            target: 承受方
            skill_name: 技能名称（用于日志）
            
        Returns:
            JudgmentResult: 判定结果
        """
        initiator_name = initiator.get_name() if hasattr(initiator, 'get_name') else str(initiator)
        target_name = target.get_name() if hasattr(target, 'get_name') else str(target)
        
        skill_info = f" (技能: {skill_name})" if skill_name else ""
        print(f"\n[判定系统] {initiator_name} vs {target_name}{skill_info}")
        
        # 双方出拳
        initiator_choice = random.choice(self.choices)
        target_choice = random.choice(self.choices)
        
        print(f"  {initiator_name} 出了: {initiator_choice}")
        print(f"  {target_name} 出了: {target_choice}")
        
        # 判定胜负
        result = self._determine_winner(initiator_choice, target_choice)
        
        if result == JudgmentResult.INITIATOR_WIN:
            print(f"  >>> {initiator_name} 获胜！")
        elif result == JudgmentResult.TARGET_WIN:
            print(f"  >>> {target_name} 获胜！")
        else:
            print(f"  >>> 平局！重新判定...")
            # 平局则重新判定
            return self._normal_rps_judgment(initiator, target, skill_name)
        
        return result
    
    def _determine_winner(self, choice1: str, choice2: str) -> JudgmentResult:
        """
        根据双方选择确定获胜者
        
        Args:
            choice1: 发起方的选择
            choice2: 承受方的选择
            
        Returns:
            JudgmentResult: 判定结果
        """
        if choice1 == choice2:
            return JudgmentResult.DRAW
        
        # 石头 > 剪刀，剪刀 > 布，布 > 石头
        winning_pairs = {
            ('石头', '剪刀'): JudgmentResult.INITIATOR_WIN,
            ('剪刀', '布'): JudgmentResult.INITIATOR_WIN,
            ('布', '石头'): JudgmentResult.INITIATOR_WIN,
            ('剪刀', '石头'): JudgmentResult.TARGET_WIN,
            ('布', '剪刀'): JudgmentResult.TARGET_WIN,
            ('石头', '布'): JudgmentResult.TARGET_WIN,
        }
        
        return winning_pairs.get((choice1, choice2), JudgmentResult.DRAW)
    
    def create_auto_win_rule(self, winner: str = "initiator") -> Callable[[Any, Any], Optional[JudgmentResult]]:
        """
        创建自动获胜规则
        
        Args:
            winner: "initiator" 或 "target"，指定自动获胜方
            
        Returns:
            规则函数
        """
        def rule(initiator: Any, target: Any) -> Optional[JudgmentResult]:
            if winner == "initiator":
                return JudgmentResult.INITIATOR_WIN
            elif winner == "target":
                return JudgmentResult.TARGET_WIN
            return None
        
        return rule
    
    def create_conditional_rule(self, 
                               condition_func: Callable[[Any, Any], bool],
                               success_result: JudgmentResult) -> Callable[[Any, Any], Optional[JudgmentResult]]:
        """
        创建条件规则：满足条件时返回指定结果，否则正常判定
        
        Args:
            condition_func: 条件函数，接受(发起方, 承受方)，返回bool
            success_result: 条件满足时的判定结果
            
        Returns:
            规则函数
        """
        def rule(initiator: Any, target: Any) -> Optional[JudgmentResult]:
            if condition_func(initiator, target):
                return success_result
            return None  # 不满足条件时正常判定
        
        return rule
