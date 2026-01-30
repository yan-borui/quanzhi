# -*- coding: utf-8 -*-
"""
角色选择界面
提供CLI界面让用户选择对战角色
"""

from typing import List, Dict
from factory.character_factory import get_character_factory, get_character_registry
from core.character import Character


def display_available_characters():
    """显示所有可用角色"""
    registry = get_character_registry()
    all_metadata = registry.get_all_metadata()
    
    print("\n" + "=" * 60)
    print("可用角色列表".center(60))
    print("=" * 60)
    
    role_ids = sorted(all_metadata.keys())
    for i, role_id in enumerate(role_ids, 1):
        metadata = all_metadata[role_id]
        display_name = metadata.get("display_name", role_id)
        description = metadata.get("description", "")
        stats = metadata.get("stats", {})
        max_hp = stats.get("max_hp", "?")
        role_type = stats.get("role_type", "")
        
        print(f"\n{i}. {display_name} (ID: {role_id})")
        print(f"   类型: {role_type}")
        print(f"   生命值: {max_hp}")
        print(f"   描述: {description}")
    
    print("=" * 60)
    return role_ids


def select_characters(min_players: int = 2, max_players: int = 6, max_retries: int = 3) -> List[Character]:
    """
    角色选择界面
    
    Args:
        min_players: 最小玩家数
        max_players: 最大玩家数
        max_retries: 最大重试次数（防止无限递归）
        
    Returns:
        选定的角色列表
    """
    factory = get_character_factory()
    registry = get_character_registry()
    
    print("\n" + "=" * 60)
    print("角色选择".center(60))
    print("=" * 60)
    print(f"\n请选择 {min_players}-{max_players} 名角色参战")
    
    # 显示可用角色
    role_ids = display_available_characters()
    
    if not role_ids:
        print("\n错误: 没有可用角色！")
        return []
    
    selected_characters = []
    
    # 获取玩家数量
    while True:
        try:
            num_input = input(f"\n请输入参战角色数量 ({min_players}-{max_players}): ").strip()
            num_players = int(num_input)
            if min_players <= num_players <= max_players:
                break
            else:
                print(f"请输入 {min_players} 到 {max_players} 之间的数字！")
        except KeyboardInterrupt:
            print("\n\n选择已取消。")
            return []
        except ValueError:
            print("无效输入，请输入数字！")
    
    # 选择每个角色
    successfully_created = 0
    while successfully_created < num_players:
        try:
            print(f"\n--- 选择第 {successfully_created + 1} 名角色 ---")
            
            # 显示可选角色（显示序号）
            print("可选角色：")
            for idx, role_id in enumerate(role_ids, 1):
                metadata = registry.get_metadata(role_id)
                display_name = metadata.get("display_name", role_id)
                print(f"{idx}. {display_name}")
            
            # 选择角色类型
            while True:
                try:
                    choice = input(f"请选择角色类型 (1-{len(role_ids)}): ").strip()
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(role_ids):
                        selected_role_id = role_ids[choice_num - 1]
                        break
                    else:
                        print(f"请输入 1-{len(role_ids)} 之间的数字！")
                except KeyboardInterrupt:
                    print("\n\n选择已取消。")
                    return []
                except ValueError:
                    print("无效输入，请输入数字！")
            
            # 可选：自定义角色名称
            metadata = registry.get_metadata(selected_role_id)
            default_name = metadata.get("display_name", selected_role_id)
            
            try:
                custom_name_input = input(f"自定义角色名称 (留空使用默认名称 '{default_name}'): ").strip()
                custom_name = custom_name_input if custom_name_input else None
            except KeyboardInterrupt:
                print("\n\n选择已取消。")
                return []
            
            # 创建角色
            character = factory.create(selected_role_id, custom_name)
            if character:
                selected_characters.append(character)
                successfully_created += 1
                print(f"已添加: {character.name}")
            else:
                print(f"错误: 无法创建角色 {selected_role_id}")
                
        except KeyboardInterrupt:
            print("\n\n选择已取消。")
            return []
    
    # 确认选择
    print("\n" + "=" * 60)
    print("已选择的角色：")
    for i, char in enumerate(selected_characters, 1):
        print(f"{i}. {char.name} (HP: {char.max_hp})")
    print("=" * 60)
    
    try:
        confirm = input("\n确认开始游戏？(y/n): ").strip().lower()
        if confirm != 'y':
            if max_retries > 0:
                print("取消选择，重新开始...")
                return select_characters(min_players, max_players, max_retries - 1)
            else:
                print("已达到最大重试次数，返回空列表。")
                return []
    except KeyboardInterrupt:
        print("\n\n选择已取消。")
        return []
    
    return selected_characters


def quick_select_default_characters() -> List[Character]:
    """快速选择默认角色（骑士、召唤师、剑客）"""
    factory = get_character_factory()
    
    print("\n使用默认角色配置：骑士、召唤师、剑客")
    
    characters = []
    for role_id in ["knight", "summoner", "swordsman"]:
        char = factory.create(role_id)
        if char:
            characters.append(char)
    
    return characters
