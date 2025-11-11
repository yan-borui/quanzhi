# -*- coding: utf-8 -*-
# main.py
import random
from Knight import Knight
from Summoner import Summoner
from Swordsman import Swordsman


class Game:
    def __init__(self):
        # 初始化三个角色
        self.knight = Knight("骑士")
        self.summoner = Summoner("召唤师")
        self.swordsman = Swordsman("剑客")

        # 所有角色的列表
        self.all_characters = [self.knight, self.summoner, self.swordsman]

        # 存活角色列表
        self.alive_characters = self.all_characters.copy()

        # 回合计数器
        self.round_count = 0

    def get_random_alive_character(self):
        """随机获取一个存活的角色"""
        return random.choice(self.alive_characters) if self.alive_characters else None

    def get_random_target(self, attacker):
        """为攻击者随机选择一个目标（不能是自己）"""
        possible_targets = [char for char in self.alive_characters if char != attacker]
        return random.choice(possible_targets) if possible_targets else None

    def get_random_skill(self, character):
        """随机获取角色可用的技能"""
        available_skills = []

        for skill_name, skill in character.skills.items():
            # 特殊技能条件检查
            if skill_name == "盾" and character.shield_charges <= 0:
                continue
            if skill_name == "齐攻":
                wolf_accum = character.get_accumulation("狼")
                bear_accum = character.get_accumulation("熊")
                if wolf_accum < 4 and bear_accum < 4:
                    continue
            if skill_name == "闪电劈":
                # 需要检查是否有目标有3层剑意
                has_valid_target = any(
                    char.get_imprint("剑意") >= 3 for char in self.alive_characters if char != character)
                if not has_valid_target:
                    continue
            if skill_name == "无敌刺":
                # 需要检查是否有目标有闪电劈控制
                has_valid_target = any(
                    char.has_control("lightning_strike") for char in self.alive_characters if char != character)
                if not has_valid_target:
                    continue

            # 检查冷却
            if skill.is_available():
                available_skills.append(skill_name)

        return random.choice(available_skills) if available_skills else None

    def update_alive_characters(self):
        """更新存活角色列表"""
        self.alive_characters = [char for char in self.all_characters if char.is_alive()]

    def display_battle_status(self):
        """显示战斗状态"""
        print(f"\n=== 第 {self.round_count} 回合开始 ===")
        for char in self.all_characters:
            status = "存活" if char.is_alive() else "已摧毁"
            print(f"{char.name}: {char.current_hp}/{char.max_hp} HP [{status}]")

    def play_round(self):
        """进行一个回合"""
        self.round_count += 1
        self.display_battle_status()

        # 每回合开始时，骑士记录状态
        if self.knight.is_alive():
            self.knight.on_turn_start()

        # 随机选择一个行动的角色
        attacker = self.get_random_alive_character()
        if not attacker:
            return False

        # 随机选择一个技能
        skill_name = self.get_random_skill(attacker)
        if not skill_name:
            print(f"{attacker.name} 没有可用技能，跳过本回合")
            return True

        # 随机选择目标
        target = self.get_random_target(attacker)
        if not target:
            print(f"{attacker.name} 没有可用目标，跳过本回合")
            return True

        # 使用技能
        print(f"\n{attacker.name} 准备使用 {skill_name} 攻击 {target.name}")
        attacker.use_skill_on_target(skill_name, target)

        # 更新存活状态
        self.update_alive_characters()

        # 检查游戏是否结束
        if len(self.alive_characters) <= 1:
            return False

        return True

    def reset_game(self):
        """重置游戏状态"""
        for char in self.all_characters:
            char.current_hp = char.max_hp
            char.control.clear()
            char.imprints.clear()
            char.accumulations.clear()
            char.clear_nearby_characters()

            # 重置角色特定状态
            if hasattr(char, 'reset_battle_round'):
                char.reset_battle_round()

            # 重置所有技能冷却
            for skill in char.skills.values():
                skill.set_cooldown(0)

        self.alive_characters = self.all_characters.copy()
        self.round_count = 0

    def start_game(self):
        """开始游戏"""
        print("=== 三国大战开始 ===")
        print("参战角色:")
        for char in self.all_characters:
            print(f"- {char.name} ({char.max_hp} HP)")

        # 初始让所有角色互相在附近（简化距离管理）
        for i, char1 in enumerate(self.all_characters):
            for char2 in self.all_characters[i + 1:]:
                char1.add_nearby_character(char2)

        # 游戏主循环
        while len(self.alive_characters) > 1:
            if not self.play_round():
                break

        # 显示游戏结果
        self.display_game_result()

    def display_game_result(self):
        """显示游戏结果"""
        print("\n=== 游戏结束 ===")
        if len(self.alive_characters) == 1:
            winner = self.alive_characters[0]
            print(f"胜利者: {winner.name}")
        else:
            print("平局！所有角色都被摧毁了")

        print(f"总回合数: {self.round_count}")
        print("\n最终状态:")
        for char in self.all_characters:
            status = "存活" if char.is_alive() else "已摧毁"
            print(f"{char.name}: {char.current_hp}/{char.max_hp} HP [{status}]")


def main():
    """主函数"""
    game = Game()
    game.start_game()

    # 可选：询问是否重新开始
    while True:
        choice = input("\n是否重新开始游戏？(y/n): ").lower()
        if choice == 'y':
            game.reset_game()
            game.start_game()
        else:
            print("游戏结束，再见！")
            break


if __name__ == "__main__":
    main()
