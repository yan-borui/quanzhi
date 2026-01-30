# -*- coding: utf-8 -*-
import sys
import unittest

sys.path.insert(0, 'include')

import factory.character_init  # noqa: E402
from factory.character_factory import get_character_factory  # noqa: E402


class TestScholarOilArray(unittest.TestCase):
    def setUp(self):
        self.factory = get_character_factory()

    def test_scholar_molotov_control(self):
        scholar = self.factory.create("scholar", "S")
        target = self.factory.create("knight", "K")
        scholar.use_skill_on_target("燃烧瓶", target)
        self.assertTrue(target.has_control("燃烧瓶"))

    def test_oil_master_limit(self):
        oil = self.factory.create("oil_master", "O")
        target = self.factory.create("knight", "K")
        oil.use_skill_on_target("倒你脸上", target)
        # second use in same round should fail due to oil_pots limit
        oil.use_skill_on_target("倒你脸上", target)
        self.assertEqual(oil.oil_pots, 0)

    def test_array_master_five_color(self):
        array = self.factory.create("array_master", "A")
        target = self.factory.create("knight", "K")
        for skill in ["瘟阵", "灰阵", "风阵", "火阵"]:
            array.use_skill_on_target(skill, target)
        pre_hp = target.current_hp
        array.use_skill_on_target("五彩法阵", target)
        self.assertEqual(max(pre_hp - 60, 0), target.current_hp)


if __name__ == "__main__":
    unittest.main()
