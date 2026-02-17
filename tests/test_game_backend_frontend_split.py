# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))

from characters.oil_master import OilMaster
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
