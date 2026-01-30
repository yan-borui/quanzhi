# -*- coding: utf-8 -*-
import sys
import unittest

sys.path.insert(0, 'include')

import factory.character_init  # noqa: E402
from factory.character_factory import get_character_factory  # noqa: E402


class TestNewCharacters(unittest.TestCase):
    def setUp(self):
        self.factory = get_character_factory()

    def test_ranger_brick_damage(self):
        ranger = self.factory.create("ranger", "R")
        target = self.factory.create("knight", "K")
        target.set_block_id(ranger.get_block_id())
        ranger.use_skill_on_target("板砖", target)
        self.assertEqual(target.max_hp - 6, target.current_hp)

    def test_healer_shield_blocks(self):
        healer = self.factory.create("healer", "H")
        target = self.factory.create("knight", "K")
        healer.use_skill_on_target("套盾", target)
        target.take_damage(5)
        self.assertEqual(target.max_hp, target.current_hp)


if __name__ == "__main__":
    unittest.main()
