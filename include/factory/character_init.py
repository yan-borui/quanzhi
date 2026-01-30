# -*- coding: utf-8 -*-
"""
角色初始化模块 - 注册所有可用角色到工厂系统
"""

from include.factory.character_factory import register_character
from include.characters.knight import Knight, KNIGHT_STATS_DATA
from include.characters.summoner import Summoner, SUMMONER_STATS_DATA
from include.characters.swordsman import Swordsman, SWORDSMAN_STATS_DATA


def initialize_characters():
    """初始化并注册所有角色"""
    
    # 注册骑士
    register_character(
        role_id="knight",
        character_class=Knight,
        display_name=KNIGHT_STATS_DATA.get("name", "骑士"),
        description=KNIGHT_STATS_DATA.get("description", ""),
        stats=KNIGHT_STATS_DATA
    )
    
    # 注册召唤师
    register_character(
        role_id="summoner",
        character_class=Summoner,
        display_name=SUMMONER_STATS_DATA.get("name", "召唤师"),
        description=SUMMONER_STATS_DATA.get("description", ""),
        stats=SUMMONER_STATS_DATA
    )
    
    # 注册剑客
    register_character(
        role_id="swordsman",
        character_class=Swordsman,
        display_name=SWORDSMAN_STATS_DATA.get("name", "剑客"),
        description=SWORDSMAN_STATS_DATA.get("description", ""),
        stats=SWORDSMAN_STATS_DATA
    )


# 模块导入时自动初始化
initialize_characters()
