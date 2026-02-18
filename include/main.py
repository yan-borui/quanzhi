# -*- coding: utf-8 -*-
# main.py
from typing import List, Optional
from core.character import Character
# 导入配置系统
from config.game_config import get_game_config
# 导入角色初始化以注册所有角色
import factory.character_init
from factory.character_selection import select_characters, quick_select_default_characters
# 从拆分后的模块导入后端类
from backend.game_backend import GameBackend, Game
from backend.game_cli import GameCLI


def main():
    config = get_game_config()

    print("=" * 60)  # Target: Current Player
    print("欢迎来到角色战斗游戏！".center(60))  # Target: Current Player
    print("=" * 60)  # Target: Current Player
    print("\n游戏模式选择：")  # Target: Current Player
    print("1. 自定义角色选择")  # Target: Current Player
    print(f"2. 使用默认角色（{', '.join(config.default_characters)}）")  # Target: Current Player

    while True:
        try:
            choice = input("\n请选择游戏模式 (1-2): ").strip()
            if choice == "1":
                characters = select_characters(
                    min_players=config.min_players,
                    max_players=config.max_players
                )
                break
            if choice == "2":
                characters = quick_select_default_characters()
                break
            print("无效选择，请输入 1 或 2")  # Target: Current Player
        except KeyboardInterrupt:
            print("\n\n游戏已退出。")  # Target: Current Player
            return
        except Exception as e:
            print(f"错误: {e}")  # Target: Current Player
            print("请重新选择")  # Target: Current Player

    if not characters:
        print("没有选择角色，游戏退出。")  # Target: Current Player
        return

    backend = GameBackend(characters)
    cli = GameCLI(backend)
    cli.run()


if __name__ == "__main__":
    main()