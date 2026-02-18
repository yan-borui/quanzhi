# -*- coding: utf-8 -*-
# game_backend.py
import random
import io
from contextlib import redirect_stdout
from typing import List, Optional
from core.character import Character
from characters.knight import Knight
from characters.summoner import Summoner
from characters.swordsman import Swordsman
from characters.oil_master import OilMaster
# 导入配置系统
from config.game_config import get_game_config
# 导入角色初始化以注册所有角色
import factory.character_init
from factory.character_selection import quick_select_default_characters
# 导入新系统
from systems.dual_judgment import DualJudgmentSystem
from systems.continuous_effect import ContinuousEffectSystem
from systems.state_binding import StateBindingSystem

from core.character import HARMLESS_CONTROLS


class GameBackend:
    def __init__(self, characters: List[Character] = None):
        self.config = get_game_config()

        if characters is None or len(characters) == 0:
            characters = quick_select_default_characters()

        self.all_characters = characters
        self.alive_characters = self.all_characters.copy()
        self.round_count = 0

        self.dual_judgment_system = DualJudgmentSystem()
        self.continuous_effect_system = ContinuousEffectSystem()
        self.state_binding_system = StateBindingSystem()

        self.initialize_block_system()

    def initialize_block_system(self):
        for char in self.all_characters:
            char.block_id = id(char)
            char.nearby_characters = [char]

    def reset_game(self):
        new_characters = []
        for char in self.all_characters:
            char_class = type(char)
            new_char = char_class(char.name)
            new_characters.append(new_char)

        self.all_characters = new_characters
        self.alive_characters = self.all_characters.copy()
        self.round_count = 0

        self.dual_judgment_system = DualJudgmentSystem()
        self.continuous_effect_system = ContinuousEffectSystem()
        self.state_binding_system = StateBindingSystem()

        self.initialize_block_system()
        return {"reset": True}

    def is_game_over(self):
        self.update_alive_characters()
        return len(self.alive_characters) <= 1 or self.round_count >= self.config.max_rounds

    def get_game_over_summary(self):
        self.update_alive_characters()
        if len(self.alive_characters) == 1:
            winner = self.alive_characters[0]
            result = {
                "type": "winner",
                "winner_name": winner.name,
                "winner_hp": winner.current_hp,
                "winner_max_hp": winner.max_hp,
            }
        elif len(self.alive_characters) == 0:
            result = {"type": "all_destroyed"}
        else:
            result = {
                "type": "draw",
                "alive_names": [char.name for char in self.alive_characters]
            }

        result["round_count"] = self.round_count
        result["max_rounds_reached"] = self.round_count >= self.config.max_rounds
        result["final_status"] = [
            {
                "name": char.name,
                "current_hp": char.current_hp,
                "max_hp": char.max_hp,
                "alive": char.is_alive(),
            }
            for char in self.all_characters
        ]
        return result

    def start_round(self):
        self.round_count += 1

        for char in self.all_characters:
            char.current_round = self.round_count

        for char in self.all_characters:
            if hasattr(char, "start_new_turn_log"):
                char.start_new_turn_log()

        for char in self.all_characters:
            if hasattr(char, 'on_turn_start'):
                char.on_turn_start()

        self.reduce_all_cooldowns()
        rps_result = self.rock_paper_scissors()

        return {
            "round_count": self.round_count,
            "battle_status": self.get_battle_status(),
            "winner": rps_result["winner"],
            "rps_logs": rps_result["logs"],
            "winner_message": None if rps_result["winner"] is None else f"本回合由 {rps_result['winner'].name} 先手！"
        }

    def finish_round(self, winner: Optional[Character]):
        for char in self.all_characters:
            if isinstance(char, Knight):
                if (char.death_shield_window_active
                        and not char.is_alive()
                        and char.death_shield_window_round == self.round_count
                        and winner is not char):
                    char.expire_death_shield_window()

        self.update_alive_characters()
        return self.get_round_end_status()

    def get_round_end_status(self):
        return {
            "round_count": self.round_count,
            "characters": [
                {
                    "name": char.name,
                    "alive": char.is_alive(),
                    "current_hp": char.current_hp,
                    "max_hp": char.max_hp,
                    "hp_bar": self.get_hp_bar(char, 15) if char.is_alive() else None,
                }
                for char in self.all_characters
            ]
        }

    def move_character_to_block(self, character: Character, target_block_id: int):
        old_block_id = character.block_id
        if old_block_id == target_block_id:
            return {"success": False, "message": f"{character.name} 已经在目标位置"}

        old_block_chars = [c for c in self.all_characters if c.block_id == old_block_id and c != character]
        for other_char in old_block_chars:
            if character in other_char.nearby_characters:
                other_char.nearby_characters.remove(character)

        character.block_id = target_block_id
        self.rebuild_all_nearby_lists()

        self.continuous_effect_system.check_and_remove_on_event(character, "movement")

        return {"success": True, "message": f"{character.name} 移动到块 {target_block_id}"}

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

        for char in self.all_characters:
            if isinstance(char, Knight):
                was_alive = char in prev_alive
                is_alive_now = char in self.alive_characters
                if was_alive and not is_alive_now:
                    char.on_death_event(self.round_count)
                elif (not was_alive) and is_alive_now:
                    char.on_revive_event()

    def get_battle_status(self):
        status = []
        for char in self.all_characters:
            status_info = []
            if char.control:
                status_info.append(f"控制:{list(char.control.keys())}")
            if char.imprints:
                status_info.append(f"印记:{char.imprints}")
            if char.accumulations:
                status_info.append(f"积累:{char.accumulations}")
            if isinstance(char, Knight) and hasattr(char, 'shield_charges'):
                status_info.append(f"盾次数:{char.shield_charges}")
            status.append({
                "character": char,
                "name": char.name,
                "alive": char.is_alive(),
                "current_hp": char.current_hp,
                "max_hp": char.max_hp,
                "hp_bar": self.get_hp_bar(char),
                "status_info": status_info,
            })
        return status

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
        participants = self.alive_characters.copy()
        logs = ["=== 石头剪刀布环节 ==="]

        for char in self.all_characters:
            if not char.is_alive() and isinstance(char, Knight) and char.can_use_shield():
                if char not in participants:
                    participants.append(char)
                    logs.append(f"{char.name} 虽已阵亡，但仍有盾技能可用，参与本回合！")

        if not participants:
            return {"winner": None, "logs": logs}

        winner = self._resolve_rps_winner(participants, logs)
        return {"winner": winner, "logs": logs}

    def _resolve_rps_winner(self, participants, logs):
        choices = ['石头', '剪刀', '布']
        player_choices = {}

        for char in participants:
            choice = random.choice(choices)
            player_choices[char] = choice
            logs.append(f"{char.name} 出了：{choice}")

        unique_choices = set(player_choices.values())

        if len(unique_choices) == 1:
            logs.append("平局！重新开始...")
            return self._resolve_rps_winner(participants, logs)

        if len(unique_choices) == 3:
            logs.append("三种都有，平局！重新开始...")
            return self._resolve_rps_winner(participants, logs)

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
            logs.append(f"{winner.name} 获胜！")
            return winner

        logs.append(f"多个赢家：{[w.name for w in winners]}，继续猜拳...")
        return self._resolve_rps_winner(winners, logs)

    def get_available_actions(self, character):
        actions = []
        active_controls = [k for k in character.control.keys() if k not in HARMLESS_CONTROLS]

        if active_controls:
            if isinstance(character, Knight) and character.can_use_shield():
                actions.append("技能:盾")
            for control_name in active_controls:
                actions.append(f"行为:解控-{control_name}")
            harmless_to_clear = HARMLESS_CONTROLS.intersection(character.control.keys()) - set(active_controls)
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

        actions.append("行为:到你身边")
        actions.append("行为:离你远点")

        for control_name in character.control.keys():
            if control_name in HARMLESS_CONTROLS:
                actions.append(f"行为:解控-{control_name}")

        for char in self.alive_characters:
            if isinstance(char, OilMaster) and char.oil_pot_count > 0:
                actions.append("[交互] 喝油 (HP+3)")
                break

        return actions

    def get_action_context(self, character):
        actions = self.get_available_actions(character)
        action_entries = []
        for i, action in enumerate(actions, 1):
            is_unavailable = any(
                marker in action for marker in ["(CD:", "(无次数)", "(条件不足)", "(历史不足)", "(上上回合有控制)", "(积累不足:", "(无有效目标)"]
            )
            action_entries.append({
                "index": i,
                "action": action,
                "is_unavailable": is_unavailable,
            })

        return {
            "character": character,
            "name": character.name,
            "current_hp": character.current_hp,
            "max_hp": character.max_hp,
            "controls": list(character.control.keys()),
            "imprints": character.imprints.copy() if character.imprints else {},
            "accumulations": character.accumulations.copy() if character.accumulations else {},
            "shield_charges": character.shield_charges if isinstance(character, Knight) and hasattr(character, 'shield_charges') else None,
            "actions": action_entries,
        }

    def get_action_targets(self, character, action):
        if action.startswith("技能:"):
            skill_name = action.replace("技能:", "").strip()

            if skill_name in ["盾", "一锅油"]:
                return {"requires_target": False, "targets": []}

            targets = list(self.alive_characters)

            if character.has_control("风阵"):
                filtered_targets = [t for t in targets if t is character or not character.is_nearby(t)]
                if not filtered_targets:
                    return {"requires_target": True, "targets": [], "error": "受到风阵影响，且没有远程目标"}
                targets = filtered_targets

            if skill_name == "回旋斩":
                targets = [t for t in targets if character.is_nearby(t)]
                if not targets:
                    return {"requires_target": False, "targets": [], "error": "回旋斩需要附近目标"}
                return {"requires_target": False, "targets": targets}

            if skill_name == "闪电劈":
                targets = [t for t in targets if t.get_imprint("剑意") >= 3]
                if not targets:
                    return {"requires_target": True, "targets": [], "error": "闪电劈没有符合条件的目标"}

            if skill_name == "无敌刺":
                targets = [
                    t for t in targets
                    if t.has_control("lightning_strike")
                    and id(t) not in character.invincible_strike_used
                ]
                if not targets:
                    return {"requires_target": True, "targets": [], "error": "无敌刺没有符合条件的目标"}

            if not targets:
                return {"requires_target": True, "targets": [], "error": "没有可用目标"}

            return {"requires_target": True, "targets": targets}

        if action.startswith("行为:"):
            behavior = action.replace("行为:", "").strip()
            if behavior == "到你身边":
                targets = [char for char in self.alive_characters if char != character]
                if not targets:
                    return {"requires_target": True, "targets": [], "error": "没有可靠近的目标"}
                return {"requires_target": True, "targets": targets}
            return {"requires_target": False, "targets": []}

        return {"requires_target": False, "targets": []}

    def execute_player_action(self, character, action, target: Optional[Character] = None) -> bool:
        if action.startswith("技能:"):
            skill_name = action.replace("技能:", "").strip()

            if skill_name in ["盾", "一锅油"]:
                self._execute_silently(character.use_skill, skill_name)
                return True

            target_info = self.get_action_targets(character, action)
            if target_info.get("error"):
                return False

            targets = target_info.get("targets", [])
            if not targets:
                return False

            if skill_name == "回旋斩":
                return self._execute_silently(character.use_whirlwind_on_targets, targets)

            if target is None or target not in targets:
                return False

            self._execute_silently(character.use_skill_on_target, skill_name, target)
            return True

        if action.startswith("行为:"):
            behavior = action.replace("行为:", "").strip()

            if behavior == "到你身边":
                if target is None:
                    return False
                move_result = self.move_character_to_block(character, target.block_id)
                return move_result["success"]

            if behavior == "离你远点":
                new_block_id = id(character) + self.round_count * 1000
                move_result = self.move_character_to_block(character, new_block_id)
                return move_result["success"]

            if behavior.startswith("解控-"):
                control_name = behavior.replace("解控-", "").strip()
                if control_name in character.control:
                    del character.control[control_name]
                    return True
                return False

        if action == "[交互] 喝油 (HP+3)":
            for char in self.alive_characters:
                if isinstance(char, OilMaster) and char.oil_pot_count > 0:
                    return self._execute_silently(char.drink_oil, character)
            return False

        return False

    @staticmethod
    def _execute_silently(func, *args, **kwargs):
        with redirect_stdout(io.StringIO()):
            return func(*args, **kwargs)

    def get_dual_judgment_system(self) -> DualJudgmentSystem:
        return self.dual_judgment_system

    def get_continuous_effect_system(self) -> ContinuousEffectSystem:
        return self.continuous_effect_system

    def get_state_binding_system(self) -> StateBindingSystem:
        return self.state_binding_system


class Game(GameBackend):
    """兼容旧测试与调用方式。"""