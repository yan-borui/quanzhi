# -*- coding: utf-8 -*-
# main.py
import random
import time
from typing import List
from core.character import Character
from characters.knight import Knight
from characters.summoner import Summoner
from characters.swordsman import Swordsman
# 导入角色初始化以注册所有角色
import factory.character_init
from factory.character_selection import select_characters, quick_select_default_characters
# 导入新系统
from systems.dual_judgment import DualJudgmentSystem, JudgmentResult
from systems.continuous_effect import ContinuousEffectSystem, ContinuousEffect, RemovalCondition
from systems.state_binding import StateBindingSystem


class Game:
    def __init__(self, characters: List[Character] = None):
        """
        初始化游戏
        
        Args:
            characters: 参战角色列表。如果为None，将使用默认配置（骑士、召唤师、剑客）
        """
        if characters is None or len(characters) == 0:
            # 使用默认角色
            characters = quick_select_default_characters()

        self.all_characters = characters
        self.alive_characters = self.all_characters.copy()
        self.round_count = 0
        
        # 初始化新系统
        self.dual_judgment_system = DualJudgmentSystem()
        self.continuous_effect_system = ContinuousEffectSystem()
        self.state_binding_system = StateBindingSystem()
        
        self.initialize_block_system()

    def initialize_block_system(self):
        for char in self.all_characters:
            char.block_id = id(char)
            char.nearby_characters = [char]

    def reset_game(self):
        print("\n=== 重置游戏 ===")
        # 重新创建所有角色（保持相同类型和名称）
        new_characters = []
        for char in self.all_characters:
            char_class = type(char)
            new_char = char_class(char.name)
            new_characters.append(new_char)

        self.all_characters = new_characters
        self.alive_characters = self.all_characters.copy()
        self.round_count = 0
        
        # 重置新系统
        self.dual_judgment_system = DualJudgmentSystem()
        self.continuous_effect_system = ContinuousEffectSystem()
        self.state_binding_system = StateBindingSystem()
        
        self.initialize_block_system()
        print("游戏已重置！\n")

    def is_game_over(self):
        self.update_alive_characters()
        if len(self.alive_characters) <= 1:
            return True
        if self.round_count >= 100:
            print("\n达到最大回合数限制！")
            return True
        return False

    def display_game_over(self):
        print("\n" + "=" * 60)
        print("=== 游戏结束 ===")
        print("=" * 60)

        if len(self.alive_characters) == 1:
            winner = self.alive_characters[0]
            print(f"\n>>> 获胜者: {winner.name}")
            print(f"    剩余生命值: {winner.current_hp}/{winner.max_hp}")
        elif len(self.alive_characters) == 0:
            print("\n所有角色同归于尽！")
        else:
            print("\n游戏平局！")
            print(f"存活角色: {[char.name for char in self.alive_characters]}")

        print(f"\n总回合数: {self.round_count}")
        print("\n最终状态:")
        for char in self.all_characters:
            status = "存活" if char.is_alive() else "已摧毁"
            print(f"  {char.name}: {char.current_hp}/{char.max_hp} HP [{status}]")

        print("=" * 60)

    def play_round(self):
        self.round_count += 1

        # 为所有角色标记当前回合（用于骑士盾的限定逻辑）
        for char in self.all_characters:
            char.current_round = self.round_count

        # 开启本回合的事件记录
        for char in self.all_characters:
            if hasattr(char, "start_new_turn_log"):
                char.start_new_turn_log()

        # 回合开始时调用 on_turn_start
        for char in self.all_characters:
            if hasattr(char, 'on_turn_start'):
                char.on_turn_start()

        self.display_battle_status()
        self.reduce_all_cooldowns()

        winner = self.rock_paper_scissors()
        if winner is None:
            print("没有角色可以行动！")
            return

        print(f"\n>>> 本回合由 {winner.name} 先手！")
        action = self.display_action_options(winner)
        success = self.execute_player_action(winner, action)

        if not success:
            print(f"\n[警告] {winner.name} 的动作未能成功执行（废步）")

        # 检查所有骑士角色的死亡盾窗口过期（针对死亡后未获得出手机会的情况）
        for char in self.all_characters:
            if isinstance(char, Knight):
                if (char.death_shield_window_active
                        and not char.is_alive()
                        and char.death_shield_window_round == self.round_count
                        and winner is not char):
                    char.expire_death_shield_window()

        self.update_alive_characters()

        print(f"\n{'=' * 60}")
        print(f"第 {self.round_count} 回合结束".center(60))
        print('=' * 60)
        for char in self.all_characters:
            if char.is_alive():
                hp_bar = self.get_hp_bar(char, 15)
                print(f"{char.name}: {hp_bar} {char.current_hp}/{char.max_hp} HP")
            else:
                print(f"{char.name}: [已摧毁]")
        print('=' * 60)

    def start(self):
        print("=" * 60)
        print("欢迎来到角色战斗游戏！".center(60))
        print("=" * 60)
        print("\n参战角色:")
        for char in self.all_characters:
            print(f"  - {char.name}: {char.max_hp} HP")
        print("\n游戏规则:")
        print("  1. 每回合通过石头剪刀布决定先手")
        print("  2. 使用技能攻击对手或执行战术动作")
        print("  3. 最后存活的角色获胜")
        print("=" * 60)

        while not self.is_game_over():
            try:
                self.play_round()
                time.sleep(0.5)
            except KeyboardInterrupt:
                print("\n\n游戏被中断！")
                choice = input("是否退出游戏？(y/n): ").strip().lower()
                if choice == 'y':
                    print("游戏已退出。")
                    return
            except Exception as e:
                print(f"\n发生错误: {e}")
                import traceback
                traceback.print_exc()
                choice = input("是否继续游戏？(y/n): ").strip().lower()
                if choice != 'y':
                    return

        self.display_game_over()
        choice = input("\n是否重新开始游戏？(y/n): ").strip().lower()
        if choice == 'y':
            self.reset_game()
            self.start()

    def run(self):
        self.start()

    def move_character_to_block(self, character: Character, target_block_id: int):
        old_block_id = character.block_id
        if old_block_id == target_block_id:
            print(f"{character.name} 已经在目标位置")
            return

        old_block_chars = [c for c in self.all_characters if c.block_id == old_block_id and c != character]
        for other_char in old_block_chars:
            if character in other_char.nearby_characters:
                other_char.nearby_characters.remove(character)

        character.block_id = target_block_id
        self.rebuild_all_nearby_lists()
        
        # 触发移动事件，检查是否需要移除持续效果
        self.continuous_effect_system.check_and_remove_on_event(character, "movement")
        
        print(f"{character.name} 移动到块 {target_block_id}")

    def rebuild_all_nearby_lists(self):
        blocks = {}
        for char in self.all_characters:
            blocks.setdefault(char.block_id, []).append(char)
        for char in self.all_characters:
            char.nearby_characters = blocks[char.block_id].copy()

    def count_characters_in_block(self, block_id: int) -> int:
        count = 0
        for char in self.all_characters:
            if char.block_id == block_id:
                count += 1
        return count

    def is_nearby(self, char1: Character, char2: Character) -> bool:
        return char1.block_id == char2.block_id

    def get_block_members(self, block_id: int) -> List[Character]:
        return [char for char in self.all_characters if char.block_id == block_id]

    def get_random_alive_character(self):
        return random.choice(self.alive_characters) if self.alive_characters else None

    def get_random_target(self, attacker):
        possible_targets = [char for char in self.alive_characters if char != attacker]
        return random.choice(possible_targets) if possible_targets else None

    def update_alive_characters(self):
        prev_alive = set(self.alive_characters)
        self.alive_characters = [char for char in self.all_characters if char.is_alive()]

        # 记录所有骑士角色的死亡/复活，以便开启/关闭"死亡后盾"窗口
        for char in self.all_characters:
            if isinstance(char, Knight):
                was_alive = char in prev_alive
                is_alive_now = char in self.alive_characters
                if was_alive and not is_alive_now:
                    # 死亡发生在当前回合
                    char.on_death_event(self.round_count)
                elif (not was_alive) and is_alive_now:
                    # 角色已复活，关闭死亡窗口
                    char.on_revive_event()

    def display_battle_status(self):
        print(f"\n{'=' * 60}")
        print(f"第 {self.round_count + 1} 回合开始".center(60))
        print('=' * 60)

        for char in self.all_characters:
            status = "存活" if char.is_alive() else "已摧毁"
            hp_bar = self.get_hp_bar(char)
            print(f"{char.name:10} [{status:4}] {hp_bar} {char.current_hp:2}/{char.max_hp:2} HP")

            status_info = []
            if char.control:
                status_info.append(f"控制:{list(char.control.keys())}")
            if char.imprints:
                status_info.append(f"印记:{char.imprints}")
            if char.accumulations:
                status_info.append(f"积累:{char.accumulations}")
            if isinstance(char, Knight) and hasattr(char, 'shield_charges'):
                status_info.append(f"盾次数:{char.shield_charges}")

            if status_info:
                print(f"           {' | '.join(status_info)}")

        print('=' * 60)

    def get_hp_bar(self, character: Character, bar_length: int = 20) -> str:
        if character.max_hp == 0:
            return '[' + ' ' * bar_length + ']'
        filled_length = int(bar_length * character.current_hp / character.max_hp)
        bar = '=' * filled_length + '-' * (bar_length - filled_length)
        return f'[{bar}]'

    def reduce_all_cooldowns(self):
        for char in self.all_characters:
            char.reduce_all_cooldowns()

    def rock_paper_scissors(self):
        print("\n=== 石头剪刀布环节 ===")
        participants = self.alive_characters.copy()

        # 检查所有死亡的骑士是否可以使用盾技能参与本回合
        for char in self.all_characters:
            if not char.is_alive() and isinstance(char, Knight) and char.can_use_shield():
                if char not in participants:
                    participants.append(char)
                    print(f"{char.name} 虽已阵亡，但仍有盾技能可用，参与本回合！")

        if not participants:
            return None

        choices = ['石头', '剪刀', '布']
        player_choices = {}

        for char in participants:
            choice = random.choice(choices)
            player_choices[char] = choice
            print(f"{char.name} 出了：{choice}")

        unique_choices = set(player_choices.values())

        if len(unique_choices) == 1:
            print("平局！重新开始...")
            return self.rock_paper_scissors()

        if len(unique_choices) == 3:
            print("三种都有，平局！重新开始...")
            return self.rock_paper_scissors()

        winning_choice = None
        if '石头' in unique_choices and '剪刀' in unique_choices:
            winning_choice = '石头'
        elif '剪刀' in unique_choices and '布' in unique_choices:
            winning_choice = '剪刀'
        elif '布' in unique_choices and '石头' in unique_choices:
            winning_choice = '布'

        winners = [char for char, choice in player_choices.items() if choice == winning_choice]

        if len(winners) == 1:
            winner = winners[0]
            print(f"{winner.name} 获胜！")
            return winner
        else:
            print(f"多个赢家：{[w.name for w in winners]}，继续猜拳...")
            temp_alive = self.alive_characters
            self.alive_characters = winners
            winner = self.rock_paper_scissors()
            self.alive_characters = temp_alive
            return winner

    def get_available_actions(self, character):
        actions = []
        harmless_controls = {"护盾", "风阵", "燃烧瓶", "火阵"}
        active_controls = [k for k in character.control.keys() if k not in harmless_controls]

        if active_controls:
            if isinstance(character, Knight) and character.can_use_shield():
                actions.append("技能:盾")
            for control_name in active_controls:
                actions.append(f"行为:解控-{control_name}")
            # 仍允许无害控制被主动解除
            harmless_to_clear = harmless_controls.intersection(character.control.keys())
            for control_name in harmless_to_clear:
                actions.append(f"行为:解控-{control_name}")
            return actions

        if not character.is_alive():
            if isinstance(character, Knight) and character.can_use_shield():
                actions.append("技能:盾")
            return actions

        for skill_name, skill in character.skills.items():
            if skill_name == "盾" and isinstance(character, Knight):
                if character.can_use_shield():
                    actions.append(f"技能:{skill_name}")
                else:
                    if character.shield_charges <= 0:
                        actions.append(f"技能:{skill_name}(无次数)")
                    elif len(character.state_history) < 2:
                        actions.append(f"技能:{skill_name}(历史不足)")
                    else:
                        actions.append(f"技能:{skill_name}(不可用)")
                continue

            if skill_name == "齐攻" and isinstance(character, Summoner):
                wolf_accum = character.get_accumulation("狼")
                bear_accum = character.get_accumulation("熊")
                if wolf_accum >= 4 or bear_accum >= 4:
                    if skill.is_available():
                        actions.append(f"技能:{skill_name}")
                    else:
                        actions.append(f"技能:{skill_name}(CD:{skill.get_cooldown()})")
                else:
                    actions.append(f"技能:{skill_name}(积累不足:狼{wolf_accum}/熊{bear_accum})")
                continue

            if skill_name == "闪电劈" and isinstance(character, Swordsman):
                has_valid_target = any(
                    char.get_imprint("剑意") >= 3
                    for char in self.alive_characters
                    if char != character
                )
                if has_valid_target:
                    if skill.is_available():
                        actions.append(f"技能:{skill_name}")
                    else:
                        actions.append(f"技能:{skill_name}(CD:{skill.get_cooldown()})")
                else:
                    actions.append(f"技能:{skill_name}(无有效目标)")
                continue

            if skill_name == "无敌刺" and isinstance(character, Swordsman):
                valid_targets = [
                    char for char in self.alive_characters
                    if char != character
                       and char.has_control("lightning_strike")
                       and id(char) not in character.invincible_strike_used
                ]
                if valid_targets:
                    if skill.is_available():
                        actions.append(f"技能:{skill_name}")
                    else:
                        actions.append(f"技能:{skill_name}(CD:{skill.get_cooldown()})")
                else:
                    actions.append(f"技能:{skill_name}(无有效目标)")
                continue

            if skill.is_available():
                actions.append(f"技能:{skill_name}")
            else:
                actions.append(f"技能:{skill_name}(CD:{skill.get_cooldown()})")

        # 自己人类增益（允许对自身施放的治疗/护盾）
        # 定义哪些角色可以自我施法
        SELF_CAST_ROLES = {"healer", "knight", "swordsman", "summoner", "ranger", "array_master", "oil_master"}

        # 在 Game 类的某处获取角色的 role_id
        # 或者在 Character 类中添加一个 role_id 属性
        if hasattr(character, 'role_id') and character.role_id in SELF_CAST_ROLES:
            actions.append("行为:自我施法")

        actions.append("行为:到你身边")
        actions.append("行为:离你远点")

        # 允许在正常行动时主动清除无害类控制（例如风阵、火阵）
        for control_name in character.control.keys():
            if control_name in harmless_controls:
                actions.append(f"行为:解控-{control_name}")
        return actions

    def display_action_options(self, character):
        print(f"\n{'=' * 60}")
        print(f"{character.name} 的回合".center(60))
        print('=' * 60)
        print(f"当前状态: HP {character.current_hp}/{character.max_hp}")

        if character.control:
            print(f"控制效果: {list(character.control.keys())}")
        if character.imprints:
            print(f"印记: {character.imprints}")
        if character.accumulations:
            print(f"积累: {character.accumulations}")
        if isinstance(character, Knight) and hasattr(character, 'shield_charges'):
            print(f"盾次数: {character.shield_charges}")

        actions = self.get_available_actions(character)

        print("\n可用动作：")
        available_actions = []
        for i, action in enumerate(actions, 1):
            is_unavailable = any(
                marker in action for marker in ["(CD:", "(无次数)", "(条件不足)", "(历史不足)", "(上上回合有控制)", "(积累不足:", "(无有效目标)"])
            if is_unavailable:
                print(f"{i}. {action} [不可用]")
            else:
                print(f"{i}. {action}")
                available_actions.append((i, action))

        while True:
            try:
                choice = input("\n请输入动作编号: ").strip()
                if choice.isdigit():
                    choice_num = int(choice)
                    if 1 <= choice_num <= len(actions):
                        selected_action = actions[choice_num - 1]
                        is_unavailable = any(marker in selected_action for marker in
                                             ["(CD:", "(无次数)", "(条件不足)", "(历史不足)", "(上上回合有控制)", "(积累不足:", "(无有效目标)"])
                        if is_unavailable:
                            print("该动作当前无法使用！")
                            continue
                        return selected_action
                    else:
                        print(f"请输入1-{len(actions)}之间的数字！")
                        continue
                print("无效的输入，请重新选择！")
            except Exception as e:
                print(f"输入错误：{e}，请重新输入！")

    def execute_player_action(self, character, action) -> bool:
        if action.startswith("技能:"):
            skill_name = action.replace("技能:", "").strip()

            if skill_name in ["盾", "狼", "熊"]:
                print(f"\n>>> {character.name} 使用技能 {skill_name}")
                character.use_skill_on_target(skill_name, character)
                return True

            targets = [char for char in self.alive_characters if char != character]

            # 风阵：仅禁止对近程目标使用技能（选择目标阶段过滤近目标）
            if character.has_control("风阵"):
                filtered_targets = [t for t in targets if not character.is_nearby(t)]
                if not filtered_targets:
                    print(f"{character.name} 受到风阵影响，无法对近程目标使用技能，且没有远程目标。")
                    return False
                targets = filtered_targets

            if skill_name == "回旋斩":
                targets = [t for t in targets if character.is_nearby(t)]
                if not targets:
                    print(f"回旋斩需要附近的目标，但没有角色在附近！")
                    return False
                # 范围伤害：对同一块内所有其他角色
                return character.use_whirlwind_on_targets(targets)
            elif skill_name == "闪电劈":
                targets = [t for t in targets if t.get_imprint("剑意") >= 3]
                if not targets:
                    print(f"闪电劈需要目标有3层剑意，但没有符合条件的目标！")
                    return False
            elif skill_name == "无敌刺":
                targets = [
                    t for t in targets
                    if t.has_control("lightning_strike")
                       and id(t) not in character.invincible_strike_used
                ]
                if not targets:
                    print(f"无敌刺需要目标有闪电劈控制效果，但没有符合条件的目标！")
                    return False

            if not targets:
                print(f"{character.name} 没有可用目标！")
                return False

            print("\n可用目标：")
            for i, target in enumerate(targets, 1):
                info = f"{target.name} (HP: {target.current_hp}/{target.max_hp})"
                if target.imprints:
                    info += f" 印记:{target.imprints}"
                if target.control:
                    info += f" 控制:{list(target.control.keys())}"
                nearby = "[近]" if character.is_nearby(target) else "[远]"
                print(f"{i}. {nearby} {info}")

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

            print(f"\n>>> {character.name} 使用技能 {skill_name} 对 {target.name}")
            character.use_skill_on_target(skill_name, target)
            return True

        elif action.startswith("行为:"):
            behavior = action.replace("行为:", "").strip()

            if behavior == "到你身边":
                targets = [char for char in self.alive_characters if char != character]
                if not targets:
                    print("没有可靠近的目标！")
                    return False

                print("\n选择要靠近的角色：")
                for i, target in enumerate(targets, 1):
                    nearby = "[已靠近]" if character.is_nearby(target) else ""
                    print(f"{i}. {target.name} {nearby}")

                while True:
                    try:
                        target_choice = input("请选择目标编号: ").strip()
                        if target_choice.isdigit():
                            target_num = int(target_choice)
                            if 1 <= target_num <= len(targets):
                                target = targets[target_num - 1]
                                self.move_character_to_block(character, target.block_id)
                                print(f">>> {character.name} 靠近了 {target.name}")
                                return True
                        print(f"请输入1-{len(targets)}之间的数字！")
                    except Exception as e:
                        print(f"输入错误：{e}")

            elif behavior == "离你远点":
                new_block_id = id(character) + self.round_count * 1000
                self.move_character_to_block(character, new_block_id)
                print(f">>> {character.name} 远离了所有角色！")
                return True

            elif behavior.startswith("解控-"):
                control_name = behavior.replace("解控-", "").strip()
                if control_name in character.control:
                    del character.control[control_name]
                    print(f">>> {character.name} 解除了 {control_name} 控制效果！")
                    return True
                else:
                    print(f"未找到控制效果：{control_name}")
                    return False
            elif behavior == "自我施法":
                # 允许对自己使用带目标的技能（简单选择第一个可用的治疗/护盾技能）
                self_targets = ["套盾", "大血包", "小血包"]
                for name in self_targets:
                    if character.has_skill(name) and character.get_skill(name).is_available():
                        print(f">>> {character.name} 对自己使用 {name}")
                        character.use_skill_on_target(name, character)
                        return True
                print("没有可用的自我施法技能！")
                return False

        return False

    # ===== 新系统访问方法 =====
    
    def get_dual_judgment_system(self) -> DualJudgmentSystem:
        """获取双人判定系统"""
        return self.dual_judgment_system
    
    def get_continuous_effect_system(self) -> ContinuousEffectSystem:
        """获取持续效果系统"""
        return self.continuous_effect_system
    
    def get_state_binding_system(self) -> StateBindingSystem:
        """获取状态绑定系统"""
        return self.state_binding_system


def main():
    print("=" * 60)
    print("欢迎来到角色战斗游戏！".center(60))
    print("=" * 60)
    print("\n游戏模式选择：")
    print("1. 自定义角色选择")
    print("2. 使用默认角色（骑士、召唤师、剑客）")

    while True:
        try:
            choice = input("\n请选择游戏模式 (1-2): ").strip()
            if choice == "1":
                # 自定义选择角色
                characters = select_characters(min_players=2, max_players=6)
                break
            elif choice == "2":
                # 使用默认角色
                characters = quick_select_default_characters()
                break
            else:
                print("无效选择，请输入 1 或 2")
        except KeyboardInterrupt:
            print("\n\n游戏已退出。")
            return
        except Exception as e:
            print(f"错误: {e}")
            print("请重新选择")

    if not characters:
        print("没有选择角色，游戏退出。")
        return

    game = Game(characters)
    game.start()


if __name__ == "__main__":
    main()
