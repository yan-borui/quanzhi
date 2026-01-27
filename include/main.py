# -*- coding: utf-8 -*-
# main.py
import random
from typing import List
from Character import Character
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
            char.nearby_characters = [char]

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

        # 为每个角色更新邻接表（直接重建，避免双向操作导致的问题）
        for char in characters_in_block:
            char.nearby_characters = []
            for other_char in characters_in_block:
                if other_char not in char.nearby_characters:
                    char.nearby_characters.append(other_char)

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

    def rock_paper_scissors(self):
        """三个角色进行石头剪刀布，返回赢家"""
        print("\n=== 石头剪刀布环节 ===")

        # 确定可参与的角色：存活的角色 + 死亡但有盾次数的骑士
        participants = self.alive_characters.copy()

        # 如果骑士死了但可以使用盾，也让它参与
        if not self.knight.is_alive() and isinstance(self.knight, Knight) and self.knight.can_use_shield():
            participants.append(self.knight)
            print(f"{self.knight.name} 虽已阵亡，但仍有盾技能可用，参与本回合！")

        if not participants:
            return None

        # 为每个参与者随机选择出拳
        choices = ['石头', '剪刀', '布']
        player_choices = {}

        for char in participants:
            choice = random.choice(choices)
            player_choices[char] = choice
            print(f"{char.name} 出了：{choice}")

        # 判断赢家
        # 如果所有人出的一样，或者三种都有，则平局，重新猜
        unique_choices = set(player_choices.values())

        if len(unique_choices) == 1:
            print("平局！重新开始...")
            return self.rock_paper_scissors()

        if len(unique_choices) == 3:
            print("三种都有，平局！重新开始...")
            return self.rock_paper_scissors()

        # 确定赢的出拳类型
        winning_choice = None
        if '石头' in unique_choices and '剪刀' in unique_choices:
            winning_choice = '石头'
        elif '剪刀' in unique_choices and '布' in unique_choices:
            winning_choice = '剪刀'
        elif '布' in unique_choices and '石头' in unique_choices:
            winning_choice = '布'

        # 找出所���赢家
        winners = [char for char, choice in player_choices.items() if choice == winning_choice]

        if len(winners) == 1:
            winner = winners[0]
            print(f"\n{winner.name} 获胜！")
            return winner
        else:
            # 多个赢家，��新在赢家之间猜拳
            print(f"\n多个赢家：{[w.name for w in winners]}，继续猜拳...")
            temp_participants = participants
            self.alive_characters = winners
            winner = self.rock_paper_scissors()
            self.alive_characters = temp_participants
            return winner

    def get_available_actions(self, character):
        """获取角色的所有可用动作选项"""
        actions = []

        # 如果角色被控制
        if character.control:
            # 骑士可以使用盾（如果满足条件）
            if isinstance(character, Knight) and character.can_use_shield():
                actions.append("技能:盾")

            # 添加解控选项
            for control_name in character.control.keys():
                actions.append(f"行为:解控-{control_name}")

            return actions

        # 如果角色死亡
        if not character.is_alive():
            # 只有骑士死后可以使用盾
            if isinstance(character, Knight) and character.can_use_shield():
                actions.append("技能:盾")
            return actions

        # 没有被控制且存活时，添加可用技能
        for skill_name, skill in character.skills.items():
            # 骑士的盾技能特殊处理
            if skill_name == "盾" and isinstance(character, Knight):
                if character.can_use_shield():
                    actions.append(f"技能:{skill_name}")
                else:
                    # 显示不可用原因
                    if character.shield_charges <= 0:
                        actions.append(f"技能:{skill_name}(无次数)")
                    else:
                        actions.append(f"技能:{skill_name}(条件不足)")
                continue

            if skill.is_available():
                actions.append(f"技能:{skill_name}")
            else:
                # 显示冷却中的技能（不可选）
                actions.append(f"技能:{skill_name}(CD:{skill.get_cooldown()})")

        # 添加行为选项
        actions.append("行为:到你身边")
        actions.append("行为:离你远点")

        return actions

    def display_action_options(self, character):
        """显示角色的所有可用动作并获取用户输入"""
        print(f"\n=== {character.name} 的回合 ===")
        print(f"当前状态: HP {character.current_hp}/{character.max_hp}")

        if character.control:
            print(f"控制效果: {list(character.control.keys())}")
        if character.imprints:
            print(f"印记: {character.imprints}")
        if character.accumulations:
            print(f"积累: {character.accumulations}")

        actions = self.get_available_actions(character)

        print("\n可用动作：")
        for i, action in enumerate(actions, 1):
            print(f"{i}. {action}")

        # 获取用户输入
        while True:
            try:
                choice = input("\n请输入动作编号或直接输入动作名称（如'游刃斩'或'到你身边'）: ").strip()

                # 尝试作为数字解析
                if choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(actions):
                        selected_action = actions[choice_num - 1]
                        # 检查是否是不可用的动作
                        if "(CD:" in selected_action or "(无次数)" in selected_action or "(条件不足)" in selected_action:
                            print("该动作当前无法使用！")
                            continue
                        return selected_action
                    else:
                        print(f"请输入1-{len(actions)}之间的数字！")
                        continue

                # 尝试作为动作名称解析
                for action in actions:
                    if "(CD:" in action or "(无次数)" in action or "(条件不足)" in action:
                        continue
                    if choice in action or action.endswith(choice):
                        return action

                print("无效的输入，请重新选择！")

            except Exception as e:
                print(f"输入错误：{e}，请重新输入！")

    def execute_player_action(self, character, action):
        """执行玩家选择的动作，返回是否成功执行"""
        # 解析动作类型
        if action.startswith("技能:"):
            skill_name = action.replace("技能:", "").strip()

            # 特殊技能：盾、狼、熊 - 目标为自己，不需要选择
            if skill_name in ["盾", "狼", "熊"]:
                print(f"\n{character.name} 使用技能 {skill_name}")

                # 记录使用前的CD状态（用于废步检测）
                old_cooldown = character.get_skill_cooldown(skill_name)

                character.use_skill_on_target(skill_name, character)

                # 检查是否是废步（技能CD未到）
                if old_cooldown > 0:
                    print(f"[废步] {skill_name} 技能冷却未完成！")
                    return False

                return True

            # 其他技能需要选择目标
            targets = [char for char in self.alive_characters if char != character]
            if not targets:
                print(f"{character.name} 没有可用目标！")
                return False

            print("\n可用目标：")
            for i, target in enumerate(targets, 1):
                print(f"{i}. {target.name} (HP: {target.current_hp}/{target.max_hp})")

            while True:
                try:
                    target_choice = input("请选择目标编号: ").strip()
                    if target_choice.isdigit():
                        target_num = int(target_choice)
                        if 1 <= target_num <= len(targets):
                            target = targets[target_num - 1]
                            break
                    print(f"请输入1-{len(targets)}之间的数字！")
                except Exception as e:
                    print(f"输入错误：{e}，请重新输入！")

            print(f"\n{character.name} 使用技能 {skill_name} 攻击 {target.name}")

            # 记录使用前的CD状态（用于废步检测）
            character.get_skill_cooldown(skill_name)

            character.use_skill_on_target(skill_name, target)
