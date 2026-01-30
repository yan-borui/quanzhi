# -*- coding: utf-8 -*-
"""
Systems module - 游戏系统
包含双人判定、持续效果、状态绑定等游戏系统
"""

from .dual_judgment import DualJudgmentSystem, JudgmentResult
from .continuous_effect import ContinuousEffectSystem, ContinuousEffect, RemovalCondition
from .state_binding import StateBindingSystem

__all__ = [
    'DualJudgmentSystem', 'JudgmentResult',
    'ContinuousEffectSystem', 'ContinuousEffect', 'RemovalCondition',
    'StateBindingSystem'
]
