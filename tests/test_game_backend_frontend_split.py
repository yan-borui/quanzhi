# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"
    ),
)

from characters.oil_master import OilMaster
from characters.target import Target
from core.player import Player
from main import GameBackend


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
