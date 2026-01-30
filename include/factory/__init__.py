# -*- coding: utf-8 -*-
"""
Factory module - 工厂和初始化
包含角色工厂、注册表和选择系统
"""

from include.factory.character_factory import (
    CharacterFactory,
    CharacterRegistry,
    get_character_factory,
    get_character_registry,
    register_character
)
from include.factory.character_selection import select_characters, quick_select_default_characters

__all__ = [
    'CharacterFactory',
    'CharacterRegistry', 
    'get_character_factory',
    'get_character_registry',
    'register_character',
    'select_characters',
    'quick_select_default_characters'
]
