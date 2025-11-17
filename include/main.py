# -*- coding: utf-8 -*-
# main.py
import random
from typing import List
from Character import Character
from Behavior import BehaviorType
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

        # 初始化块系统
        self.initialize_block_system()

    def initialize_block_system(self):
        """初始化块系统，每个角色在自己的块中"""
        # 初始时每个角色在自己的块，邻接表只包含自己
        for char in self.all_characters:
            char.block_id = id(char)
            char.clear_nearby_characters()
            char.add_nearby_character(char)  # 每个角色总是靠近自己

    def move_character_to_block(self, character: Character, target_block_id: int):
        """将角色移动到目标块"""
        old_block_id = character.block_id

        if old_block_id == target_block_id:
            return  # 已经在目标块中

        # 更新角色的块ID
        character.block_id = target_block_id

        # 更新邻接表：角色与目标块中的所有角色互相靠近
        self.update_nearby_for_block(target_block_id)

        # 如果原块中还有其他角色，也需要更新他们的邻接表
        if self.count_characters_in_block(old_block_id) > 0:
            self.update_nearby_for_block(old_block_id)

        print(f"{character.name} 移动到块 {target_block_id}")

    def count_characters_in_block(self, block_id: int) -> int:
        """计算块中的角色数量"""
        count = 0
        for char in self.all_characters:
            if char.block_id == block_id:
                count += 1
        return count

    def update_nearby_for_block(self, block_id: int):
        """更新指定块中所有角色的邻接表"""
        # 获取该块中的所有角色
        characters_in_block = [char for char in self.all_characters if char.block_id == block_id]

        # 为每个角色更新邻接表
        for char in characters_in_block:
            # 清空当前邻接表
            char.clear_nearby_characters()

            # 添加该块中的所有角色到邻接表
            for other_char in characters_in_block:
                char.add_nearby_character(other_char)

        print(f"块 {block_id} 更新完成，包含角色: {[c.name for c in characters_in_block]}")

    def is_nearby(self, char1: Character, char2: Character) -> bool:
        """检查两个角色是否在同一块中（是否靠近）"""
        return char1.block_id == char2.block_id

    def get_block_members(self, block_id: int) -> List[Character]:
        """获取指定块中的所有角色"""
        return [char for char in self.all_characters if char.block_id == block_id]

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

    def reduce_all_cooldowns(self):
        """所有角色的技能冷却减少1回合"""
        for char in self.all_characters:
            char.reduce_all_cooldowns()

    def play_round(self):
        """进行一个回合"""
        self.round_count += 1
        self.display_battle_status()

        # 新增：在回合开始时减少所有角色的技能冷却
        self.reduce_all_cooldowns()

        # 每回合开始时，骑士记录状态
        if self.knight.is_alive():
            self.knight.on_turn_start()

        # 随机选择一个行动的角色
        attacker = self.get_random_alive_character()
        if not attacker:
            return False

        # 检查角色是否被控制
        if attacker.is_controlled():
            # 被控制时只能选择解控行为
            print(f"{attacker.name} 被控制，本回合只能选择解控行为")
            self.perform_remove_control_behavior(attacker)
            return True

        # 随机决定是使用技能、执行移动行为还是解控行为
        action_type = random.choice(["skill", "move_behavior", "remove_control"])

        if action_type == "skill":
            # 使用技能的逻辑
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
            print(f"\n{attacker.name} 使用技能 {skill_name} 攻击 {target.name}")
            attacker.use_skill_on_target(skill_name, target)

        elif action_type == "move_behavior":
            # 执行移动行为的逻辑
            target = self.get_random_target(attacker)

            if not target:
                print(f"{attacker.name} 没有可用目标，无法执行移动行为，跳过本回合")
                return True

            self.perform_random_move_behavior(attacker, target)

        else:  # remove_control
            # 执行解控行为
            self.perform_remove_control_behavior(attacker)

        # 更新存活状态
        self.update_alive_characters()

        # 检查游戏是否结束
        if len(self.alive_characters) <= 1:
            return False

        return True

    def perform_random_move_behavior(self, attacker, target):
        """随机执行一种移动行为"""
        behavior = random.choice([BehaviorType.MOVE_CLOSE, BehaviorType.MOVE_AWAY])

        print(f"\n{attacker.name} 执行移动行为: {behavior.value} 针对 {target.name}")

        if behavior == BehaviorType.MOVE_CLOSE:
            # 靠近目标：移动到目标所在的块
            target_block_id = target.block_id
            self.move_character_to_block(attacker, target_block_id)
            attacker.set_behavior(behavior)

        else:
            # 远离目标：创建新块（移动到自己的块）
            attacker_block_id = id(attacker)
            self.move_character_to_block(attacker, attacker_block_id)
            attacker.set_behavior(behavior)

    def perform_remove_control_behavior(self, attacker):
        """执行解控行为"""
        print(f"\n{attacker.name} 执行解控行为")

        # 检查是否有控制效果
        if not attacker.control:
            print(f"{attacker.name} 没有控制效果可解控，跳过本回合")
            return

        # 随机选择一个控制效果进行移除
        control_name = random.choice(list(attacker.control.keys()))
        attacker.reduce_control(control_name, 1)
        attacker.set_behavior(BehaviorType.REMOVE_CONTROL)

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

        # 重置块系统
        self.initialize_block_system()

        self.alive_characters = self.all_characters.copy()
        self.round_count = 0

    def start_game(self):
        """开始游戏"""
        print("=== 三国大战开始 ===")
        print("参战角色:")
        for char in self.all_characters:
            print(f"- {char.name} ({char.max_hp} HP)")

        # 显示初始块状态
        print("\n初始块状态:")
        blocks = {}
        for char in self.all_characters:
            if char.block_id not in blocks:
                blocks[char.block_id] = []
            blocks[char.block_id].append(char.name)

        for block_id, names in blocks.items():
            print(f"块 {block_id}: {names}")

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
