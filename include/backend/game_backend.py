# -*- coding: utf-8 -*-
# game_backend.py
import random
import io
from contextlib import redirect_stdout
from typing import List, Optional
from core.character import Character
from core.event_log import emit, silence_events
from characters.knight import Knight
from characters.oil_master import OilMaster
from characters.warlock import Warlock
from characters.scythe_worker import ScytheWorker
from characters.ninja import Ninja
from characters.chicken_master import ChickenMaster
from characters.scientist import Scientist
from characters.scholar import Scholar

# 导入配置系统
from config.game_config import get_game_config

# 导入角色初始化以注册所有角色
import factory.character_init
from factory.character_selection import quick_select_default_characters

# 导入新系统
from systems.dual_judgment import DualJudgmentSystem
from systems.continuous_effect import ContinuousEffectSystem
from systems.state_binding import StateBindingSystem
from dataclasses import replace
from backend.actions import (
    ActionOption,
    ActionResult,
    TargetMode,
    action_option_from_legacy,
)
from backend.battle_state import BattleRoster, BoardState
from backend.rounds import RoundPhase, RoundPipeline


class GameBackend:
    def __init__(self, characters: List[Character] = None):
        self.config = get_game_config()

        if characters is None or len(characters) == 0:
            characters = quick_select_default_characters()

        self.roster = BattleRoster(characters)
        self.board = BoardState(self.roster)
        self.round_count = 0

        self.dual_judgment_system = DualJudgmentSystem()
        self.continuous_effect_system = ContinuousEffectSystem()
        self.state_binding_system = StateBindingSystem()
        self.round_pipeline = self._build_round_pipeline()

        self.initialize_block_system()
        self._inject_systems_to_characters()

    @property
    def all_characters(self):
        """旧调用方兼容 Adapter；写入应通过 roster。"""
        return self.roster.all

    @property
    def alive_characters(self):
        """旧调用方兼容 Adapter；刷新应通过 roster。"""
        return self.roster.alive

    def _inject_systems_to_characters(self):
        """将系统级实例注入需要它们的角色"""
        for char in self.all_characters:
            if isinstance(char, ScytheWorker):
                char.set_state_binding_system(self.state_binding_system)
            if isinstance(char, Ninja):
                char.set_state_binding_system(self.state_binding_system)
                char.set_dual_judgment_system(self.dual_judgment_system)
                char.set_continuous_effect_system(self.continuous_effect_system)
            if isinstance(char, Scholar):
                char.set_continuous_effect_system(self.continuous_effect_system)

    def initialize_block_system(self):
        self.board.initialize()

    def reset_game(self):
        new_characters = []
        for char in self.all_characters:
            # 跳过小机器人，随科学家重置自动消失
            if getattr(char, "is_mini_robot", False):
                continue
            char_class = type(char)
            new_char = char_class(char.name)
            new_characters.append(new_char)

        self.roster.replace(new_characters)
        self.round_count = 0

        self.dual_judgment_system = DualJudgmentSystem()
        self.continuous_effect_system = ContinuousEffectSystem()
        self.state_binding_system = StateBindingSystem()

        self._inject_systems_to_characters()
        self.initialize_block_system()
        return {"reset": True}

    def is_game_over(self):
        self.update_alive_characters()
        real_alive = [
            c for c in self.alive_characters if not getattr(c, "is_mini_robot", False)
        ]
        return len(real_alive) <= 1 or self.round_count >= self.config.max_rounds

    def get_game_over_summary(self):
        self.update_alive_characters()
        real_alive = [
            c for c in self.alive_characters if not getattr(c, "is_mini_robot", False)
        ]
        if len(real_alive) == 1:
            winner = real_alive[0]
            result = {
                "type": "winner",
                "winner_name": winner.name,
                "winner_hp": winner.current_hp,
                "winner_max_hp": winner.max_hp,
            }
        elif len(real_alive) == 0:
            result = {"type": "all_destroyed"}
        else:
            result = {
                "type": "draw",
                "alive_names": [char.name for char in real_alive],
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
        context = self.round_pipeline.run()
        rps_result = context["rps_result"]
        return {
            "round_count": self.round_count,
            "battle_status": self.get_battle_status(),
            "winner": rps_result["winner"],
            "rps_logs": rps_result["logs"],
            "winner_message": (
                None
                if rps_result["winner"] is None
                else f"本回合由 {rps_result['winner'].name} 先手！"
            ),
            "phase_trace": context["phase_trace"],
        }

    def _build_round_pipeline(self) -> RoundPipeline:
        return RoundPipeline(
            [
                (RoundPhase.OPEN, self._phase_open_round),
                (RoundPhase.CHARACTER_START, self._phase_character_start),
                (RoundPhase.CONTINUOUS_EFFECTS, self._phase_continuous_effects),
                (RoundPhase.DEATH_RESOLUTION, self._phase_death_resolution),
                (RoundPhase.COOLDOWN, self._phase_cooldown),
                (RoundPhase.INITIATIVE, self._phase_initiative),
            ]
        )

    def _phase_open_round(self, context: dict):
        self.round_count += 1
        for char in self.all_characters:
            char.current_round = self.round_count
        for char in self.all_characters:
            if hasattr(char, "start_new_turn_log"):
                char.start_new_turn_log()

    def _phase_character_start(self, context: dict):
        for char in self.all_characters:
            if hasattr(char, "on_turn_start"):
                char.on_turn_start()

    def _phase_continuous_effects(self, context: dict):
        self._trigger_continuous_effects()

    def _phase_death_resolution(self, context: dict):
        self.update_alive_characters()

    def _phase_cooldown(self, context: dict):
        self.reduce_all_cooldowns()

    def _phase_initiative(self, context: dict):
        real_alive = [
            c for c in self.alive_characters if not getattr(c, "is_mini_robot", False)
        ]
        if len(real_alive) <= 1:
            rps_result = {
                "winner": None,
                "logs": ["=== 石头剪刀布环节 ===", "持续效果结算后游戏已结束。"],
            }
        else:
            rps_result = self.rock_paper_scissors()
        context["rps_result"] = rps_result

    def finish_round(self, winner: Optional[Character]):
        for char in self.all_characters:
            if isinstance(char, Knight):
                if (
                    char.death_shield_window_active
                    and not char.is_alive()
                    and char.death_shield_window_round == self.round_count
                    and winner is not char
                ):
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
            ],
        }

    def move_character_to_block(self, character: Character, target_block_id: int):
        if not self.board.move(character, target_block_id):
            return {"success": False, "message": f"{character.name} 已经在目标位置"}

        self.continuous_effect_system.check_and_remove_on_event(character, "movement")

        return {
            "success": True,
            "message": f"{character.name} 移动到块 {target_block_id}",
        }

    def move_character_to_random_new_block(self, character: Character):
        """将角色移动到一个随机且当前未占用的新地块。"""
        new_block_id = self.board.random_empty_block(
            self.continuous_effect_system.block_effects
        )
        return self.move_character_to_block(character, new_block_id)

    def _trigger_continuous_effects(self):
        for char in list(self.all_characters):
            self.continuous_effect_system.trigger_all_effects(char)

        blocks = {}
        for char in self.all_characters:
            blocks.setdefault(char.block_id, []).append(char)
        for block_id, members in blocks.items():
            self.continuous_effect_system.trigger_block_effects(block_id, members)

    def rebuild_all_nearby_lists(self):
        self.board.rebuild_nearby_cache()

    def count_characters_in_block(self, block_id: int) -> int:
        return self.board.count(block_id)

    def is_nearby(self, char1: Character, char2: Character) -> bool:
        return char1.block_id == char2.block_id

    def get_block_members(self, block_id: int) -> List[Character]:
        return self.board.members(block_id)

    def get_random_alive_character(self):
        return random.choice(self.alive_characters) if self.alive_characters else None

    def get_random_target(self, attacker):
        possible_targets = [char for char in self.alive_characters if char != attacker]
        return random.choice(possible_targets) if possible_targets else None

    def update_alive_characters(self):
        prev_alive = self.roster.was_alive()
        self.roster.refresh_alive()

        for char in self.all_characters:
            if isinstance(char, Knight):
                was_alive = char in prev_alive
                is_alive_now = char in self.alive_characters
                if was_alive and not is_alive_now:
                    char.on_death_event(self.round_count)
                elif (not was_alive) and is_alive_now:
                    char.on_revive_event()

        # 吃鸡大师复活检测：如果有待复活标记，执行复活
        for char in self.all_characters:
            if isinstance(char, ChickenMaster) and char.pending_revive:
                if char.try_revive():
                    self.roster.register(char)

        # 若有角色携带死亡之门死亡，检查是否需要重置术士冷却
        self._check_death_gate_cleared()

    def get_battle_status(self):
        status = []
        for char in self.all_characters:
            status_info = []
            if char.control:
                status_info.append(f"控制:{list(char.control.keys())}")
            if char.imprints:
                status_info.append(f"印记:{char.imprints}")
            if char.resources:
                status_info.append(f"资源:{char.resources}")
            if char.modifiers:
                status_info.append(f"战斗修正:{char.modifiers}")
            if isinstance(char, Knight) and hasattr(char, "shield_charges"):
                status_info.append(f"盾次数:{char.shield_charges}")
            if isinstance(char, ChickenMaster):
                status_info.append(f"空投:{char.airdrop_count}")
            if isinstance(char, Scientist):
                status_info.append(f"电池:{char.battery_count}")
                status_info.append(f"机器人:{char.robot_count}")
                if char.in_robot_mode:
                    status_info.append("机器人模式")
            if getattr(char, "is_mini_robot", False):
                owner = char._owner
                status_info.append(f"[小机器人] 归属:{owner.name}")
            status.append(
                {
                    "character": char,
                    "name": char.name,
                    "alive": char.is_alive(),
                    "current_hp": char.current_hp,
                    "max_hp": char.max_hp,
                    "hp_bar": self.get_hp_bar(char),
                    "status_info": status_info,
                }
            )
        return status

    def get_hp_bar(self, character: Character, bar_length: int = 20) -> str:
        if character.max_hp == 0:
            return "[" + " " * bar_length + "]"
        filled_length = int(bar_length * character.current_hp / character.max_hp)
        bar = "=" * filled_length + "-" * (bar_length - filled_length)
        return f"[{bar}]"

    def reduce_all_cooldowns(self):
        for char in self.all_characters:
            char.reduce_all_cooldowns()

    def rock_paper_scissors(self):
        # 小机器人不参与石头剪刀布
        participants = [
            c for c in self.alive_characters if not getattr(c, "is_mini_robot", False)
        ]
        logs = ["=== 石头剪刀布环节 ==="]

        for char in self.all_characters:
            if (
                not char.is_alive()
                and isinstance(char, Knight)
                and char.can_use_shield()
            ):
                if char not in participants:
                    participants.append(char)
                    logs.append(f"{char.name} 虽已阵亡，但仍有盾技能可用，参与本回合！")

        if not participants:
            return {"winner": None, "logs": logs}

        if len(participants) == 1:
            winner = participants[0]
            logs.append(f"{winner.name} 是唯一可行动角色。")
            return {"winner": winner, "logs": logs}

        winner = self._resolve_rps_winner(participants, logs)
        return {"winner": winner, "logs": logs}

    def _resolve_rps_winner(self, participants, logs):
        choices = ["石头", "剪刀", "布"]
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
        if "石头" in unique_choices and "剪刀" in unique_choices:
            winning_choice = "石头"
        elif "剪刀" in unique_choices and "布" in unique_choices:
            winning_choice = "剪刀"
        elif "布" in unique_choices and "石头" in unique_choices:
            winning_choice = "布"

        winners = [
            char for char, choice in player_choices.items() if choice == winning_choice
        ]

        if len(winners) == 1:
            winner = winners[0]
            logs.append(f"{winner.name} 获胜！")
            return winner

        logs.append(f"多个赢家：{[w.name for w in winners]}，继续猜拳...")
        return self._resolve_rps_winner(winners, logs)

    def get_available_actions(self, character):
        actions = []
        active_controls = character.get_blocking_controls()

        if active_controls:
            actions.extend(character.available_when_controlled_actions(self))
            for control_name in active_controls:
                actions.append(f"行为:解控-{control_name}")
            for control_name in character.get_non_blocking_controls():
                actions.append(f"行为:解控-{control_name}")
            return actions

        if not character.is_alive():
            return character.available_when_defeated_actions(self)

        for skill_name, skill in character.skills.items():
            actions.append(character.describe_skill_action(skill_name, skill, self))

        actions.append("行为:到你身边")
        actions.append("行为:离你远点")

        for control_name in character.get_non_blocking_controls():
            actions.append(f"行为:解控-{control_name}")

        # 搜索隐身角色（忍者忍法地心）
        stealthed_chars = [
            c
            for c in self.alive_characters
            if c != character and isinstance(c, Ninja) and c.in_stealth
        ]
        for ninja_char in stealthed_chars:
            actions.append(f"行为:搜索-{ninja_char.name}")

        for char in self.alive_characters:
            if isinstance(char, OilMaster) and char.oil_pot_count > 0:
                actions.append("[交互] 喝油 (HP+3)")
                break

        return actions

    def get_action_context(self, character):
        action_options = self.get_action_options(character)
        action_entries = [
            option.to_dict(index) for index, option in enumerate(action_options, 1)
        ]

        return {
            "character": character,
            "name": character.name,
            "current_hp": character.current_hp,
            "max_hp": character.max_hp,
            "controls": list(character.control.keys()),
            "imprints": character.imprints.copy() if character.imprints else {},
            "resources": character.resources.copy() if character.resources else {},
            "modifiers": character.modifiers.copy() if character.modifiers else {},
            "accumulations": (
                character.accumulations.copy() if character.accumulations else {}
            ),
            "shield_charges": (
                character.shield_charges
                if isinstance(character, Knight)
                and hasattr(character, "shield_charges")
                else None
            ),
            "actions": action_entries,
        }

    def get_action_options(self, character) -> List[ActionOption]:
        """返回结构化动作；旧字符串只在兼容 Adapter 中解析。"""
        options = []
        for action in self.get_available_actions(character):
            option = action_option_from_legacy(action)
            if option.enabled:
                option = self._with_targeting(character, option)
            options.append(option)
        return options

    def _with_targeting(self, character, option: ActionOption) -> ActionOption:
        target_info = self.get_action_targets(character, option.legacy_action or "")
        error = target_info.get("error")
        if error:
            return replace(option, enabled=False, disabled_reason=error)
        if target_info.get("multi_select"):
            mode = TargetMode.MULTI
        elif not target_info.get("requires_target", False):
            mode = (
                TargetMode.AUTOMATIC if target_info.get("targets") else TargetMode.NONE
            )
        else:
            mode = TargetMode.SINGLE
        return replace(option, target_mode=mode)

    def resolve_action(
        self, character, submitted_action: str
    ) -> Optional[ActionOption]:
        """按稳定 ID 或旧展示字符串解析当前动作。"""
        for option in self.get_action_options(character):
            if submitted_action in {option.action_id, option.legacy_action}:
                return option
        return None

    def _is_action_executable(self, character, action: str) -> bool:
        """检查动作是否出现在当前可执行动作列表中。"""
        if not isinstance(action, str) or not action:
            return False

        option = self.resolve_action(character, action)
        return option is not None and option.enabled

    def get_action_targets(self, character, action):
        if action.startswith("技能:"):
            skill_name = action.replace("技能:", "").strip()

            if skill_name in ["盾", "一锅油"]:
                return {"requires_target": False, "targets": []}

            targets = list(self.alive_characters)

            if character.has_control("风阵"):
                filtered_targets = [
                    t for t in targets if t is character or not character.is_nearby(t)
                ]
                if not filtered_targets:
                    return {
                        "requires_target": True,
                        "targets": [],
                        "error": "受到风阵影响，且没有远程目标",
                    }
                targets = filtered_targets

            if skill_name == "回旋斩":
                targets = [
                    t for t in targets if character.is_nearby(t) and t is not character
                ]
                if not targets:
                    return {
                        "requires_target": False,
                        "targets": [],
                        "error": "回旋斩需要附近敌方目标",
                    }
                return {"requires_target": False, "targets": targets}

            if skill_name == "闪电劈":
                targets = [t for t in targets if t.get_imprint("剑意") >= 3]
                if not targets:
                    return {
                        "requires_target": True,
                        "targets": [],
                        "error": "闪电劈没有符合条件的目标",
                    }

            if skill_name == "无敌刺":
                targets = [
                    t
                    for t in targets
                    if t.has_control("lightning_strike")
                    and id(t) not in character.invincible_strike_used
                ]
                if not targets:
                    return {
                        "requires_target": True,
                        "targets": [],
                        "error": "无敌刺没有符合条件的目标",
                    }

            # --- 术士：爆炸锁定死亡之门目标，死亡之门由玩家多选目标 ---
            if skill_name == "爆炸" and isinstance(character, Warlock):
                explosion_targets = [
                    t
                    for t in self.alive_characters
                    if t != character and t.has_control("死亡之门")
                ]
                if not explosion_targets:
                    return {
                        "requires_target": False,
                        "targets": [],
                        "error": "没有携带死亡之门的目标",
                    }
                return {"requires_target": False, "targets": explosion_targets}

            if skill_name == "死亡之门" and isinstance(character, Warlock):
                gate_targets = [
                    t for t in targets if t != character and t.is_targetable()
                ]
                return {
                    "requires_target": True,
                    "multi_select": True,
                    "targets": gate_targets,
                }

            # --- 镰刀工：忍法地心自身技能 ---
            if skill_name == "忍法地心" and isinstance(character, Ninja):
                return {"requires_target": False, "targets": []}

            # --- 忍者：摔只能对铁索覆身目标使用 ---
            if skill_name == "摔" and isinstance(character, Ninja):
                bound_target = character.state_binding_system.get_bound_target(
                    character, "铁索覆身"
                )
                if (
                    bound_target
                    and bound_target.has_control("铁索覆身")
                    and bound_target.is_alive()
                ):
                    return {"requires_target": True, "targets": [bound_target]}
                return {
                    "requires_target": True,
                    "targets": [],
                    "error": "摔没有铁索目标",
                }

            # --- 镰刀工：飞镰斩只能对身上有飞镰标记的目标使用 ---
            if skill_name == "飞镰斩" and isinstance(character, ScytheWorker):
                targets = [
                    t for t in targets if t.has_control("飞镰") and t.is_targetable()
                ]
                if not targets:
                    return {
                        "requires_target": True,
                        "targets": [],
                        "error": "飞镰斩没有飞镰目标",
                    }
                return {"requires_target": True, "targets": targets}

            # --- 镰刀工：黑暗飞镰只能对_dark_scythe_target使用 ---
            if skill_name == "黑暗飞镰" and isinstance(character, ScytheWorker):
                dark_target = character._dark_scythe_target
                if dark_target and dark_target.is_alive():
                    return {"requires_target": True, "targets": [dark_target]}
                return {
                    "requires_target": True,
                    "targets": [],
                    "error": "黑暗飞镰无可用目标",
                }

            # --- 镰刀工：挥镰排除仍被挥镰控制中的目标 ---
            if skill_name == "挥镰" and isinstance(character, ScytheWorker):
                targets = [
                    t
                    for t in targets
                    if (t is character or t.is_targetable())
                    and id(t) not in character._swing_controlled_targets
                ]
                if not targets:
                    return {
                        "requires_target": True,
                        "targets": [],
                        "error": "挥镰没有可用目标",
                    }

            # --- 吃鸡大师：空投和电池为自身技能 ---
            if skill_name == "空投" and isinstance(character, ChickenMaster):
                return {"requires_target": False, "targets": []}

            # --- 科学家：电池和制造机器人为自身技能 ---
            if isinstance(character, Scientist):
                if skill_name in ("电池", "制造机器人"):
                    return {"requires_target": False, "targets": []}
                # 小机器人不能被科学家自身的撸/自爆选为目标（排除自己的机器人）
                targets = [
                    t
                    for t in targets
                    if not (
                        getattr(t, "is_mini_robot", False)
                        and getattr(t, "_owner", None) is character
                    )
                ]

            # 隐身过滤：普通技能不能选中隐身目标（除非是自身技能）
            targets = [t for t in targets if t is character or t.is_targetable()]

            if not targets:
                return {"requires_target": True, "targets": [], "error": "没有可用目标"}

            return {"requires_target": True, "targets": targets}

        if action.startswith("行为:"):
            behavior = action.replace("行为:", "").strip()
            if behavior == "到你身边":
                targets = [char for char in self.alive_characters if char != character]
                if not targets:
                    return {
                        "requires_target": True,
                        "targets": [],
                        "error": "没有可靠近的目标",
                    }
                return {"requires_target": True, "targets": targets}
            return {"requires_target": False, "targets": []}

        return {"requires_target": False, "targets": []}

    def execute_player_action(
        self,
        character,
        action,
        target: Optional[Character] = None,
        selected_targets: Optional[List[Character]] = None,
    ) -> bool:
        option = self.resolve_action(character, action)
        if option is None or not option.enabled:
            return False
        action = option.legacy_action or action

        if action.startswith("技能:"):
            skill_name = action.replace("技能:", "").strip()

            if skill_name in ["盾", "一锅油"]:
                self._execute_silently(character.use_skill, skill_name)
                return True

            target_info = self.get_action_targets(character, action)
            if target_info.get("error"):
                return False

            targets = target_info.get("targets", [])

            # --- 自身技能（无需目标和targets列表） ---
            if not target_info.get("requires_target", True) and not targets:
                # 吃鸡大师空投、科学家电池/制造机器人、忍者忍法地心
                if skill_name == "空投" and isinstance(character, ChickenMaster):
                    self._execute_silently(character.use_skill, skill_name)
                    return True
                if skill_name == "电池" and isinstance(character, Scientist):
                    self._execute_silently(character.use_skill, skill_name)
                    return True
                if skill_name == "制造机器人" and isinstance(character, Scientist):
                    self._execute_silently(character.use_skill, skill_name)
                    # 将新建的小机器人加入游戏
                    for robot in character.get_named_robots():
                        if robot not in self.all_characters:
                            robot.block_id = character.block_id
                            robot.nearby_characters = [robot]
                            self.roster.register(robot)
                            self.board.rebuild_nearby_cache()
                            emit(f"小机器人 [{robot.name}] 加入战场！")
                    return True
                if skill_name == "忍法地心" and isinstance(character, Ninja):
                    self._execute_silently(character.use_skill, skill_name)
                    self.move_character_to_random_new_block(character)
                    return True

            if not targets:
                return False

            if skill_name == "回旋斩":
                return self._execute_silently(
                    character.use_whirlwind_on_targets, targets
                )

            # --- 术士多目标技能 ---
            if skill_name == "爆炸" and isinstance(character, Warlock):
                return self._execute_silently(
                    character.use_explosion_on_targets,
                    targets,
                    self._remove_control_from_character,
                )

            if skill_name == "死亡之门" and isinstance(character, Warlock):
                # 优先使用玩家主动选择的目标列表
                final_gate_targets = (
                    selected_targets if selected_targets is not None else targets
                )
                if not final_gate_targets:
                    return False
                return self._execute_silently(
                    character.use_death_gate_on_targets, final_gate_targets
                )

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
                return self._remove_control_from_character(character, control_name)

            # 搜索隐身忍者
            if behavior.startswith("搜索-"):
                ninja_name = behavior.replace("搜索-", "").strip()
                for char in self.alive_characters:
                    if (
                        isinstance(char, Ninja)
                        and char.name == ninja_name
                        and char.in_stealth
                    ):
                        return char.be_searched(character)
                return False

        if action == "[交互] 喝油 (HP+3)":
            for char in self.alive_characters:
                if isinstance(char, OilMaster) and char.oil_pot_count > 0:
                    return self._execute_silently(char.drink_oil, character)
            return False

        return False

    def execute_behavior_intent(
        self, character: Character, behavior: str, target: Optional[Character] = None
    ) -> ActionResult:
        """执行前端无关的行为意图。"""
        if behavior == "taunt":
            return ActionResult(True, f"{character.name} 嘲讽了一番，什么也没有发生。")

        if behavior == "away":
            if self.count_characters_in_block(character.block_id) <= 1:
                return ActionResult(
                    True, f"{character.name} 试图远离所有人，但本来就独处。"
                )
            success = self.execute_player_action(character, "behavior:离你远点")
            message = (
                f"{character.name} 远离了所有人。"
                if success
                else f"{character.name} 试图远离所有人，但没有发生变化。"
            )
            return ActionResult(success, message)

        if behavior == "approach":
            if target is None or not target.is_alive() or target is character:
                return ActionResult(
                    True, f"{character.name} 试图靠近一个无效目标，什么也没有发生。"
                )
            success = self.execute_player_action(
                character, "behavior:到你身边", target=target
            )
            message = (
                f"{character.name} 来到了 {target.name} 身边。"
                if success
                else f"{character.name} 试图靠近 {target.name}，但没有发生变化。"
            )
            return ActionResult(success, message)

        if behavior == "search":
            if (
                target is None
                or not target.is_alive()
                or not isinstance(target, Ninja)
                or not target.in_stealth
            ):
                return ActionResult(
                    True, f"{character.name} 试图搜索，但没有有效的隐身目标。"
                )
            found = self._execute_silently(target.be_searched, character)
            message = (
                f"{character.name} 成功找出了隐身中的 {target.name}。"
                if found
                else f"{character.name} 试图寻找 {target.name}，但没有成功。"
            )
            return ActionResult(True, message)

        return ActionResult(False, f"{character.name} 提交了未知行动。", retry=True)

    def apply_skill_cooldown_multiplier(
        self, character: Character, action: str, multiplier: int
    ):
        """应用对局级技能冷却倍率。"""
        option = self.resolve_action(character, action)
        if option is None or option.kind.value != "skill":
            return
        skill = character.get_skill(option.name)
        if skill is None:
            return
        if multiplier == 0:
            skill.set_cooldown(0)
        elif multiplier != 1 and skill.get_cooldown() > 0:
            skill.scale_cooldown(multiplier)

    @staticmethod
    def _execute_silently(func, *args, **kwargs):
        with silence_events(), redirect_stdout(io.StringIO()):
            return func(*args, **kwargs)

    def get_dual_judgment_system(self) -> DualJudgmentSystem:
        return self.dual_judgment_system

    def get_continuous_effect_system(self) -> ContinuousEffectSystem:
        return self.continuous_effect_system

    def get_state_binding_system(self) -> StateBindingSystem:
        return self.state_binding_system

    def _notify_control_removal(self, target: Character, control_name: str):
        """
        当目标解除控制效果时，通知相关角色（镰刀工/忍者等）。
        用于联动解除状态绑定。
        """
        for char in self.all_characters:
            if isinstance(char, ScytheWorker) and hasattr(
                char, "notify_target_removed_control"
            ):
                char.notify_target_removed_control(target, control_name)
            if isinstance(char, Ninja) and hasattr(
                char, "notify_target_removed_control"
            ):
                char.notify_target_removed_control(target, control_name)

        # 当死亡之门被解除时，检查是否所有死亡之门都已清空
        if control_name == "死亡之门":
            self._check_death_gate_cleared()

    def _remove_control_from_character(
        self, target: Character, control_name: str
    ) -> bool:
        if not target.has_control(control_name):
            return False

        target.clear_control(control_name)
        self._notify_control_removal(target, control_name)
        return True

    def _check_death_gate_cleared(self):
        """检查场上是否还有死亡之门；若全部清除，重置术士状态并设置2回合冷却。"""
        has_active_gate = any(
            char.has_control("死亡之门") for char in self.alive_characters
        )
        if not has_active_gate:
            for char in self.all_characters:
                if isinstance(char, Warlock) and char._death_gate_active:
                    char._death_gate_active = False
                    char._death_gate_initial_count = 0
                    death_gate_skill = char.get_skill("死亡之门")
                    if death_gate_skill:
                        death_gate_skill.start_cooldown(2)


class Game(GameBackend):
    """兼容旧测试与调用方式。"""
