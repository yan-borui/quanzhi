# -*- coding: utf-8 -*-
"""
Systems module - 游戏系统
包含双人判定、持续效果、状态绑定等游戏系统
"""

from systems.dual_judgment import DualJudgmentSystem, JudgmentResult
from systems.continuous_effect import ContinuousEffectSystem, ContinuousEffect, RemovalCondition
from systems.state_binding import StateBindingSystem

__all__ = [
    'DualJudgmentSystem', 'JudgmentResult',
    'ContinuousEffectSystem', 'ContinuousEffect', 'RemovalCondition',
    'StateBindingSystem'
]
