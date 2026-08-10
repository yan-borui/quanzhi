# -*- coding: utf-8 -*-
import sys
import os
import random

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"
    ),
)

from characters.scholar import Scholar
from characters.oil_master import OilMaster
from characters.ranger import Ranger
from characters.scientist import Scientist
from characters.target import Target
from characters.warlock import Warlock
from characters.summoner import Summoner
from core.event_log import event_sink, silence_events
from core.player import Player
from core.skill import Skill
from main import GameBackend
from systems.continuous_effect import (
    ContinuousEffect,
    RemovalCondition,
)


def test_backend_execute_action_has_no_stdout(capsys):
    oil_master = OilMaster()
    oil_master.oil_pot_count = 1
    target = Player("战士", 60)
    target.set_current_hp(50)

    game = GameBackend([oil_master, target])
    result = game.execute_player_action(target, "[交互] 喝油 (HP+3)")

    captured = capsys.readouterr()
    assert result is True
    assert captured.out == ""


def test_backend_returns_structured_action_context():
    oil_master = OilMaster()
    target = Player("战士", 60)
    game = GameBackend([oil_master, target])

    context = game.get_action_context(target)

    assert isinstance(context, dict)
    assert "actions" in context
    assert isinstance(context["actions"], list)
    action = context["actions"][0]
    assert action["id"]
    assert action["kind"] in {"skill", "behavior", "interaction"}
    assert isinstance(action["enabled"], bool)


def test_disabled_action_has_structured_reason():
    summoner = Summoner("召唤师")
    game = GameBackend([summoner, Target("目标")])

    action = next(
        item
        for item in game.get_action_context(summoner)["actions"]
        if item["id"] == "skill:齐攻"
    )

    assert action["enabled"] is False
    assert action["disabled_reason"] == "积累不足:狼0/熊0"


def test_backend_accepts_stable_action_id():
    attacker = Target("攻击者")
    defender = Target("防御者")
    game = GameBackend([attacker, defender])

    assert game.execute_player_action(attacker, "skill:平A", target=defender)
    assert defender.current_hp == defender.max_hp - 6


def test_backend_owns_behavior_intent_rules():
    actor = Target("行动者")
    target = Target("目标")
    game = GameBackend([actor, target])

    outcome = game.execute_behavior_intent(actor, "approach", target)

    assert outcome.success
    assert actor.block_id == target.block_id


def test_roster_and_board_keep_registration_invariants():
    actor = Target("行动者")
    game = GameBackend([actor, Target("目标")])
    newcomer = Target("新角色")

    game.board.register(newcomer, actor.block_id)

    assert newcomer in game.all_characters
    assert newcomer in game.alive_characters
    assert newcomer in game.get_block_members(actor.block_id)
    assert actor.is_nearby(newcomer)
    assert newcomer in actor.get_nearby_characters()
    assert actor in newcomer.get_nearby_characters()


def test_legacy_roster_registration_refreshes_board_cache():
    actor = Target("行动者")
    game = GameBackend([actor, Target("目标")])
    newcomer = Target("新角色")
    newcomer.set_block_id(actor.block_id)

    game.roster.register(newcomer)

    assert newcomer in actor.get_nearby_characters()
    assert actor in newcomer.get_nearby_characters()


def test_forced_move_syncs_board_without_removing_movement_effect():
    ranger = Ranger("游侠")
    target = Target("目标")
    game = GameBackend([ranger, target])
    effect = ContinuousEffect(
        "移动后消失",
        -1,
        lambda _: None,
        removal_condition=RemovalCondition.ON_MOVEMENT,
    )
    game.continuous_effect_system.add_effect(target, effect)

    assert game.execute_player_action(ranger, "skill:纱袋", target=target)

    assert target.block_id == ranger.block_id
    assert target in ranger.get_nearby_characters()
    assert ranger in target.get_nearby_characters()
    assert game.continuous_effect_system.get_effects(target) == [effect]


def test_regular_move_still_removes_movement_effect():
    actor = Target("行动者")
    target = Target("目标")
    game = GameBackend([actor, target])
    effect = ContinuousEffect(
        "移动后消失",
        -1,
        lambda _: None,
        removal_condition=RemovalCondition.ON_MOVEMENT,
    )
    game.continuous_effect_system.add_effect(actor, effect)

    result = game.move_character_to_block(actor, target.block_id)

    assert result["success"] is True
    assert game.continuous_effect_system.get_effects(actor) == []


def test_robot_registration_keeps_roster_and_board_in_sync():
    scientist = Scientist("科学家")
    game = GameBackend([scientist, Target("目标")])
    scientist.add_resource("电池", 4)
    scientist.set_pending_robot_name("一号")

    assert game.execute_player_action(scientist, "skill:制造机器人")

    robot = scientist.get_named_robots()[0]
    assert robot in game.all_characters
    assert robot in game.alive_characters
    assert robot in game.get_block_members(scientist.block_id)
    assert robot in scientist.get_nearby_characters()
    assert scientist in robot.get_nearby_characters()


def test_reset_rebinds_replacement_characters_to_board_state():
    old_actor = Target("行动者")
    game = GameBackend([old_actor, Target("目标")])

    game.reset_game()

    new_actor, new_target = game.all_characters
    assert new_actor is not old_actor
    new_actor.set_block_id(new_target.block_id)
    assert new_actor in new_target.get_nearby_characters()
    assert new_target in new_actor.get_nearby_characters()

    old_actor.set_block_id(new_target.block_id)
    assert old_actor not in new_target.get_nearby_characters()


def test_round_pipeline_exposes_stable_phase_order(monkeypatch):
    game = GameBackend([Target("甲"), Target("乙")])
    choices = iter(["石头", "剪刀"])
    monkeypatch.setattr(random, "choice", lambda _: next(choices))

    result = game.start_round()

    assert result["phase_trace"] == [
        "open",
        "character_start",
        "continuous_effects",
        "death_resolution",
        "cooldown",
        "initiative",
    ]


def test_cooldown_multiplier_resolves_action_after_skill_execution():
    scholar = Scholar("学者")
    target = Target("目标")
    game = GameBackend([scholar, target])

    assert game.execute_player_action(scholar, "skill:星星射线", target=target)
    game.apply_skill_cooldown_multiplier(scholar, "skill:星星射线", 2)

    assert scholar.get_skill("星星射线").get_cooldown() == 2


def test_legacy_adapter_preserves_parenthesized_skill_names():
    actor = Target("行动者")
    actor.add_or_replace_skill(Skill("测试(强化)", cooldown=0))
    game = GameBackend([actor, Target("目标")])

    option = next(
        item
        for item in game.get_action_context(actor)["actions"]
        if item["id"] == "skill:测试(强化)"
    )

    assert option["enabled"] is True


def test_control_metadata_separates_blocking_and_non_blocking_controls():
    actor = Target("行动者")
    defender = Target("防御者")
    game = GameBackend([actor, defender])

    actor.add_control("护盾", 1)
    assert actor.is_controlled() is False
    assert "技能:平A" in game.get_available_actions(actor)
    assert "行为:解控-护盾" in game.get_available_actions(actor)

    actor.add_control("眩晕", 1)
    assert actor.is_controlled() is True
    actions = game.get_available_actions(actor)
    assert "技能:平A" not in actions
    assert "行为:解控-眩晕" in actions
    assert "行为:解控-护盾" in actions


def test_resources_and_modifiers_are_separate_with_legacy_lookup():
    actor = Target("行动者")
    game = GameBackend([actor, Target("防御者")])

    actor.add_accumulation("电池", 2)
    actor.add_accumulation("易伤", 20)
    context = game.get_action_context(actor)

    assert actor.resources == {"电池": 2}
    assert actor.modifiers == {"易伤": 20}
    assert actor.get_accumulation("电池") == 2
    assert actor.get_accumulation("易伤") == 20
    assert context["resources"] == {"电池": 2}
    assert context["modifiers"] == {"易伤": 20}
    assert context["accumulations"] == {"电池": 2, "易伤": 20}


def test_role_describes_special_skill_availability():
    summoner = Summoner("召唤师")
    target = Target("目标")
    game = GameBackend([summoner, target])

    assert "技能:齐攻(积累不足:狼0/熊0)" in game.get_available_actions(summoner)

    summoner.add_resource("狼", 6)

    actions = game.get_available_actions(summoner)
    assert "技能:齐攻" in actions
    assert "技能:齐攻(积累不足:狼0/熊0)" not in actions


def test_domain_events_can_be_silenced_and_captured(capsys):
    target = Target("目标")

    with silence_events():
        target.take_damage(1)

    captured = capsys.readouterr()
    assert captured.out == ""

    events = []
    with event_sink(events.append):
        target.heal(1)

    captured = capsys.readouterr()
    assert captured.out == ""
    assert any("恢复了 1 点生命值" in event for event in events)


def test_backend_rejects_skill_on_cooldown():
    attacker = Target("攻击者")
    defender = Target("防御者")
    game = GameBackend([attacker, defender])
    attacker.get_skill("平A").set_cooldown(3)

    result = game.execute_player_action(attacker, "技能:平A", target=defender)

    assert result is False
    assert defender.current_hp == defender.max_hp


def test_backend_rejects_action_not_available_while_controlled():
    attacker = Target("攻击者")
    defender = Target("防御者")
    game = GameBackend([attacker, defender])
    attacker.add_control("眩晕", 1)

    result = game.execute_player_action(attacker, "技能:平A", target=defender)

    assert result is False
    assert defender.current_hp == defender.max_hp


def test_backend_rejects_no_target_skill_on_cooldown():
    oil_master = OilMaster()
    target = Target("防御者")
    game = GameBackend([oil_master, target])
    oil_master.get_skill("一锅油").set_cooldown(3)

    result = game.execute_player_action(oil_master, "技能:一锅油")

    assert result is False
    assert oil_master.oil_pot_count == 0


def test_molotov_uses_continuous_effect_system(monkeypatch):
    scholar = Scholar("学者")
    target = Target("目标")
    game = GameBackend([scholar, target])

    result = game.execute_player_action(scholar, "技能:燃烧瓶", target=target)
    assert result is True
    assert game.continuous_effect_system.get_block_effects(target.block_id)

    choices = iter(["石头", "剪刀"])
    monkeypatch.setattr(random, "choice", lambda _: next(choices))
    before_hp = target.current_hp

    game.start_round()

    assert target.current_hp == before_hp - 3


def test_continuous_effects_can_end_round_before_rps(monkeypatch):
    scholar = Scholar("学者")
    target = Target("目标")
    target.set_current_hp(1)
    game = GameBackend([scholar, target])
    assert game.execute_player_action(scholar, "技能:燃烧瓶", target=target) is True

    def fail_if_rps_runs(_):
        raise AssertionError("RPS should not run after continuous effects end the game")

    monkeypatch.setattr(random, "choice", fail_if_rps_runs)

    round_data = game.start_round()

    assert round_data["winner"] is None
    assert target.is_alive() is False
    assert "持续效果结算后游戏已结束。" in round_data["rps_logs"]


def test_backend_control_removal_records_turn_log():
    attacker = Target("攻击者")
    defender = Target("防御者")
    game = GameBackend([attacker, defender])
    attacker.add_control("眩晕", 1)
    attacker.start_new_turn_log()

    result = game.execute_player_action(attacker, "行为:解控-眩晕")

    assert result is True
    assert not attacker.has_control("眩晕")
    assert attacker.turn_effects_history[-1]["control_remove"]["眩晕"] == 1


def test_warlock_explosion_uses_backend_control_removal():
    warlock = Warlock("术士")
    target = Target("目标")
    game = GameBackend([warlock, target])
    target.add_control("死亡之门", 1)
    target.start_new_turn_log()
    warlock._death_gate_active = True
    warlock._death_gate_initial_count = 1

    result = game.execute_player_action(warlock, "技能:爆炸")

    assert result is True
    assert not target.has_control("死亡之门")
    assert target.turn_effects_history[-1]["control_remove"]["死亡之门"] == 1
    assert warlock._death_gate_active is False
    death_gate = warlock.get_skill("死亡之门")
    assert not death_gate.is_available()
    death_gate.reduce_cooldown()
    assert not death_gate.is_available()
    death_gate.reduce_cooldown()
    assert not death_gate.is_available()
    death_gate.reduce_cooldown()
    assert death_gate.is_available()
