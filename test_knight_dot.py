import sys
import unittest

sys.path.append("include")

from characters.knight import Knight  # noqa: E402
from core.character import add_burning_block, BURNING_BLOCKS  # noqa: E402


class KnightDotTest(unittest.TestCase):
    def tearDown(self):
        # 清理燃烧印记，避免影响其他测试
        BURNING_BLOCKS.clear()

    def test_knight_takes_burning_and_fire_array_damage(self):
        knight = Knight()
        add_burning_block(knight.block_id, 1)
        knight.control["火阵"] = 1

        knight.start_new_turn_log()
        knight.on_turn_start()

        # 初始60HP - 燃烧瓶每层3点*1 - 火阵每层2点*1 = 55
        self.assertEqual(knight.current_hp, 55)
        self.assertTrue(knight.is_controlled())
        self.assertEqual(BURNING_BLOCKS.get(knight.block_id), 1)


if __name__ == "__main__":
    unittest.main()
