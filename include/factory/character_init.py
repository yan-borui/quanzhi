# -*- coding: utf-8 -*-
"""
角色初始化模块 - 注册所有可用角色到工厂系统
支持内置角色注册和插件化角色加载
"""

import os

from factory.character_factory import register_character
from characters.knight import Knight, KNIGHT_STATS_DATA
from characters.summoner import Summoner, SUMMONER_STATS_DATA
from characters.swordsman import Swordsman, SWORDSMAN_STATS_DATA
from characters.ranger import Ranger, RANGER_STATS_DATA
from characters.array_master import ArrayMaster, ARRAY_MASTER_STATS_DATA
from characters.healer import Healer, HEALER_STATS_DATA
from characters.scholar import Scholar, SCHOLAR_STATS_DATA
from characters.oil_master import OilMaster, OIL_MASTER_STATS_DATA
from characters.target import Target, TARGET_STATS_DATA


def initialize_characters():
    """初始化并注册所有内置角色"""
    
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
    
    # 注册游侠
    register_character(
        role_id="ranger",
        character_class=Ranger,
        display_name=RANGER_STATS_DATA.get("name", "游侠"),
        description=RANGER_STATS_DATA.get("description", ""),
        stats=RANGER_STATS_DATA
    )
    
    # 注册阵鬼
    register_character(
        role_id="array_master",
        character_class=ArrayMaster,
        display_name=ARRAY_MASTER_STATS_DATA.get("name", "阵鬼"),
        description=ARRAY_MASTER_STATS_DATA.get("description", ""),
        stats=ARRAY_MASTER_STATS_DATA
    )
    
    # 注册治疗师
    register_character(
        role_id="healer",
        character_class=Healer,
        display_name=HEALER_STATS_DATA.get("name", "治疗师"),
        description=HEALER_STATS_DATA.get("description", ""),
        stats=HEALER_STATS_DATA
    )
    
    # 注册魔道学者
    register_character(
        role_id="scholar",
        character_class=Scholar,
        display_name=SCHOLAR_STATS_DATA.get("name", "魔道学者"),
        description=SCHOLAR_STATS_DATA.get("description", ""),
        stats=SCHOLAR_STATS_DATA
    )
    
    # 注册卖油翁
    register_character(
        role_id="oil_master",
        character_class=OilMaster,
        display_name=OIL_MASTER_STATS_DATA.get("name", "卖油翁"),
        description=OIL_MASTER_STATS_DATA.get("description", ""),
        stats=OIL_MASTER_STATS_DATA
    )
    
    # 注册靶子
    register_character(
        role_id="target",
        character_class=Target,
        display_name=TARGET_STATS_DATA.get("name", "靶子"),
        description=TARGET_STATS_DATA.get("description", ""),
        stats=TARGET_STATS_DATA
    )


def initialize_plugins():
    """加载插件目录中的角色插件"""
    from config.game_config import get_game_config
    from factory.plugin_loader import init_plugin_loader

    config = get_game_config()

    if not config.plugins_enabled:
        return

    # 解析插件目录路径（相对于项目根目录，即include的父目录）
    plugins_dir = config.plugins_directory
    if not os.path.isabs(plugins_dir):
        # __file__ = include/factory/character_init.py
        # 向上三级到达项目根目录
        include_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        project_root = os.path.dirname(include_dir)
        plugins_dir = os.path.join(project_root, plugins_dir)

    loader = init_plugin_loader(plugins_dir)

    if config.plugins_auto_load:
        loader.load_all_plugins()

    if config.hot_reload_enabled:
        loader.start_watching(config.watch_interval)


# 模块导入时自动初始化内置角色和插件
initialize_characters()
initialize_plugins()
