import json
import os
import sys
import time
import unittest

sys.path.append("include")

from config.game_config import GameConfig, _deep_merge, _deep_copy_dict  # noqa: E402
from factory.plugin_loader import PluginLoader  # noqa: E402
from factory.character_factory import CharacterRegistry, CharacterFactory  # noqa: E402


class TestGameConfig(unittest.TestCase):
    """测试配置驱动系统"""

    def test_default_config_values(self):
        config = GameConfig()
        self.assertEqual(config.max_rounds, 100)
        self.assertEqual(config.min_players, 2)
        self.assertEqual(config.max_players, 6)
        self.assertEqual(config.default_characters, ["knight", "summoner", "swordsman"])
        self.assertEqual(config.round_delay, 0.5)
        self.assertTrue(config.plugins_enabled)
        self.assertFalse(config.hot_reload_enabled)

    def test_load_from_file(self):
        config_data = {
            "game": {
                "max_rounds": 50,
                "default_characters": ["knight"]
            }
        }
        config_path = "/tmp/test_game_config.json"
        with open(config_path, 'w') as f:
            json.dump(config_data, f)

        try:
            config = GameConfig(config_path)
            self.assertEqual(config.max_rounds, 50)
            self.assertEqual(config.default_characters, ["knight"])
            # Defaults should still be present
            self.assertEqual(config.min_players, 2)
            self.assertEqual(config.round_delay, 0.5)
        finally:
            os.remove(config_path)

    def test_load_missing_file(self):
        config = GameConfig("/tmp/nonexistent_config.json")
        # Should fall back to defaults
        self.assertEqual(config.max_rounds, 100)

    def test_load_invalid_json(self):
        config_path = "/tmp/invalid_config.json"
        with open(config_path, 'w') as f:
            f.write("not valid json{{{")

        try:
            config = GameConfig(config_path)
            self.assertEqual(config.max_rounds, 100)
        finally:
            os.remove(config_path)

    def test_get_dot_path(self):
        config = GameConfig()
        self.assertEqual(config.get("game.max_rounds"), 100)
        self.assertEqual(config.get("plugins.enabled"), True)
        self.assertIsNone(config.get("nonexistent"))
        self.assertEqual(config.get("nonexistent", "fallback"), "fallback")

    def test_set_dot_path(self):
        config = GameConfig()
        config.set("game.max_rounds", 200)
        self.assertEqual(config.max_rounds, 200)

        config.set("custom.new_key", "value")
        self.assertEqual(config.get("custom.new_key"), "value")

    def test_reload(self):
        config_path = "/tmp/test_reload_config.json"
        with open(config_path, 'w') as f:
            json.dump({"game": {"max_rounds": 30}}, f)

        try:
            config = GameConfig(config_path)
            self.assertEqual(config.max_rounds, 30)

            # Modify the file
            with open(config_path, 'w') as f:
                json.dump({"game": {"max_rounds": 60}}, f)

            config.reload()
            self.assertEqual(config.max_rounds, 60)
        finally:
            os.remove(config_path)

    def test_get_all_returns_copy(self):
        config = GameConfig()
        all_config = config.get_all()
        all_config["game"]["max_rounds"] = 999
        # Original should not be affected
        self.assertEqual(config.max_rounds, 100)


class TestDeepMerge(unittest.TestCase):
    """测试深度合并工具函数"""

    def test_deep_merge_simple(self):
        base = {"a": 1, "b": 2}
        override = {"b": 3, "c": 4}
        _deep_merge(base, override)
        self.assertEqual(base, {"a": 1, "b": 3, "c": 4})

    def test_deep_merge_nested(self):
        base = {"x": {"a": 1, "b": 2}}
        override = {"x": {"b": 3}}
        _deep_merge(base, override)
        self.assertEqual(base, {"x": {"a": 1, "b": 3}})

    def test_deep_copy_dict(self):
        original = {"a": {"b": [1, 2]}, "c": 3}
        copy = _deep_copy_dict(original)
        copy["a"]["b"].append(3)
        self.assertEqual(len(original["a"]["b"]), 2)


class TestPluginLoader(unittest.TestCase):
    """测试插件加载系统"""

    def setUp(self):
        self.test_plugins_dir = "/tmp/test_plugins"
        os.makedirs(self.test_plugins_dir, exist_ok=True)

    def tearDown(self):
        import shutil
        if os.path.exists(self.test_plugins_dir):
            shutil.rmtree(self.test_plugins_dir)

    def _write_plugin(self, filename, role_id="test_role", max_hp=30):
        filepath = os.path.join(self.test_plugins_dir, filename)
        content = f'''
from core.character import Character
from core.skill import Skill

ROLE_ID = "{role_id}"

class TestCharacter(Character):
    def __init__(self, name="测试"):
        super().__init__(name, max_hp={max_hp}, control={{}}, stealth=0)
    def use_skill(self, skill_name): pass

STATS_DATA = {{"name": "测试角色", "max_hp": {max_hp}, "description": "测试插件"}}
'''
        with open(filepath, 'w') as f:
            f.write(content)
        return filepath

    def test_discover_empty_dir(self):
        loader = PluginLoader(self.test_plugins_dir)
        self.assertEqual(loader.discover_plugins(), [])

    def test_discover_plugins(self):
        self._write_plugin("test_char.py")
        loader = PluginLoader(self.test_plugins_dir)
        plugins = loader.discover_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertTrue(plugins[0].endswith("test_char.py"))

    def test_discover_ignores_underscore_files(self):
        self._write_plugin("_private.py")
        self._write_plugin("public.py", role_id="public")
        loader = PluginLoader(self.test_plugins_dir)
        plugins = loader.discover_plugins()
        self.assertEqual(len(plugins), 1)

    def test_discover_nonexistent_dir(self):
        loader = PluginLoader("/tmp/nonexistent_plugins_dir")
        self.assertEqual(loader.discover_plugins(), [])

    def test_load_plugin(self):
        filepath = self._write_plugin("test_char.py", role_id="test_load")
        loader = PluginLoader(self.test_plugins_dir)
        result = loader.load_plugin(filepath)
        self.assertTrue(result)
        self.assertIn(filepath, loader.get_loaded_plugins())

    def test_load_all_plugins(self):
        self._write_plugin("char_a.py", role_id="char_a")
        self._write_plugin("char_b.py", role_id="char_b")
        loader = PluginLoader(self.test_plugins_dir)
        loaded = loader.load_all_plugins()
        self.assertEqual(loaded, 2)

    def test_load_invalid_plugin(self):
        filepath = os.path.join(self.test_plugins_dir, "bad.py")
        with open(filepath, 'w') as f:
            f.write("# no Character subclass here\nx = 1\n")
        loader = PluginLoader(self.test_plugins_dir)
        result = loader.load_plugin(filepath)
        self.assertFalse(result)

    def test_reload_plugin(self):
        filepath = self._write_plugin("reload_test.py", role_id="reload_test", max_hp=30)
        loader = PluginLoader(self.test_plugins_dir)
        loader.load_plugin(filepath)

        # Modify the plugin
        time.sleep(0.1)
        self._write_plugin("reload_test.py", role_id="reload_test", max_hp=55)

        result = loader.reload_plugin(filepath)
        self.assertTrue(result)

    def test_check_and_reload_changed_new_file(self):
        loader = PluginLoader(self.test_plugins_dir)
        loader.load_all_plugins()

        # Add a new plugin
        self._write_plugin("new_char.py", role_id="new_char")

        reloaded = loader.check_and_reload_changed()
        self.assertEqual(len(reloaded), 1)

    def test_check_and_reload_changed_modified(self):
        filepath = self._write_plugin("mod_test.py", role_id="mod_test", max_hp=30)
        loader = PluginLoader(self.test_plugins_dir)
        loader.load_plugin(filepath)

        # Modify the file
        time.sleep(0.1)
        self._write_plugin("mod_test.py", role_id="mod_test", max_hp=55)

        reloaded = loader.check_and_reload_changed()
        self.assertEqual(len(reloaded), 1)

    def test_default_role_id_from_filename(self):
        """如果插件没有导出 ROLE_ID，使用文件名"""
        filepath = os.path.join(self.test_plugins_dir, "auto_id.py")
        content = '''
from core.character import Character

class AutoChar(Character):
    def __init__(self, name="自动"):
        super().__init__(name, max_hp=20, control={}, stealth=0)
    def use_skill(self, skill_name): pass
'''
        with open(filepath, 'w') as f:
            f.write(content)

        loader = PluginLoader(self.test_plugins_dir)
        result = loader.load_plugin(filepath)
        self.assertTrue(result)


if __name__ == "__main__":
    unittest.main()
