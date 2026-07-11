from backend.game_backend import GameBackend
from characters.chicken_master import ChickenMaster
from characters.ninja import Ninja
from characters.scientist import Scientist
from characters.target import Target
from systems.continuous_effect import ContinuousEffect
from core.damage import DamageEvent


def test_death_hook_clears_controls_even_for_direct_death_paths():
    target = Target("目标")
    target.add_control("眩晕", 1)
    target.set_current_hp(0)

    target.on_destroy()

    assert target.control == {}


def test_non_healer_shield_absorbs_attack_without_overflow():
    target = Target("目标")
    target.add_modifier("立盾", 3)

    target.take_damage(10)

    assert target.current_hp == target.max_hp
    assert target.get_modifier("立盾") == 0


def test_non_healer_shield_keeps_remaining_hp_when_not_broken():
    target = Target("目标")
    target.add_modifier("立盾", 6)

    target.take_damage(2)

    assert target.current_hp == target.max_hp
    assert target.get_modifier("立盾") == 4


def test_shield_protects_scientist_in_robot_mode():
    scientist = Scientist()
    scientist.add_resource("电池", 4)
    scientist.use_skill_on_target("制造机器人", scientist)
    scientist._in_robot_mode = True
    scientist.max_hp = 1
    scientist.current_hp = 1
    scientist.add_modifier("立盾", 3)

    scientist.take_damage(10)

    assert scientist.robot_count == 1
    assert scientist.get_modifier("立盾") == 0


def test_ninja_stealth_clears_damage_over_time_and_leaves_burning_block():
    ninja = Ninja("忍者")
    target = Target("目标")
    game = GameBackend([ninja, target])
    old_block = ninja.block_id
    ninja.add_control("火阵", 1)
    game.continuous_effect_system.add_effect(
        ninja,
        ContinuousEffect("测试持续伤害", -1, lambda affected: affected.take_damage(3)),
    )
    game.continuous_effect_system.add_block_effect(
        old_block,
        ContinuousEffect("燃烧瓶", -1, lambda affected: affected.take_damage(3)),
    )

    assert game.execute_player_action(ninja, "技能:忍法地心")

    assert not ninja.has_control("火阵")
    assert game.continuous_effect_system.get_effects(ninja) == []
    assert ninja.block_id != old_block
    assert game.continuous_effect_system.get_block_effects(ninja.block_id) == []
    assert game.continuous_effect_system.get_block_effects(old_block)


def test_scientist_battle_reset_restores_original_health():
    scientist = Scientist()
    scientist.max_hp = 1
    scientist.current_hp = 1

    scientist.reset_battle_round()

    assert scientist.max_hp == 60
    assert scientist.current_hp == 60


def test_chicken_master_battle_reset_restores_original_health():
    chicken_master = ChickenMaster()
    chicken_master.max_hp = 15
    chicken_master.current_hp = 15

    chicken_master.reset_battle_round()

    assert chicken_master.max_hp == 60
    assert chicken_master.current_hp == 60


def test_damage_event_uses_same_resolution_pipeline():
    target = Target("目标")
    target.add_modifier("易伤", 20)

    target.receive_damage(DamageEvent(amount=10, skill_name="测试技能"))

    assert target.current_hp == 48
    assert target.get_modifier("易伤") == 0


def test_damage_event_breaks_ninja_stealth():
    ninja = Ninja("忍者")
    ninja._in_stealth = True
    ninja.stealth = 1

    ninja.receive_damage(DamageEvent(amount=1))

    assert not ninja.in_stealth
    assert ninja.stealth == 0
