# -*- coding: utf-8 -*-
"""
test_plugin_loader.py - PluginLoader 测试
验证加载、卸载、重载逻辑以及插件校验集成
"""

import os
import sys
import tempfile
import textwrap

from factory.character_factory import get_character_registry, CharacterRegistry
from factory.plugin_loader import PluginLoader


def _write_plugin(directory, filename, content):
    """写入插件文件到临时目录"""
    filepath = os.path.join(directory, filename)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(textwrap.dedent(content))
    return filepath


class TestPluginLoaderLoadPlugin:
    """load_plugin 方法测试"""

    def setup_method(self):
        """每个测试方法前重置注册表"""
        registry = get_character_registry()
        for role_id in list(registry.list_available_characters()):
            registry.unregister(role_id)

    def test_load_valid_plugin(self, tmp_path):
        """合格插件应被成功加载"""
        filepath = _write_plugin(tmp_path, "valid_plugin.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = "valid_test"
            STATS_DATA = {"name": "测试角色", "max_hp": 60}

            class ValidChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        loader = PluginLoader(str(tmp_path))
        assert loader.load_plugin(filepath) is True

        registry = get_character_registry()
        assert "valid_test" in registry.list_available_characters()

    def test_load_plugin_no_character_class(self, tmp_path):
        """没有 Character 子类的插件应被拒绝"""
        filepath = _write_plugin(tmp_path, "bad_plugin.py", """\
            ROLE_ID = "bad_test"
            STATS_DATA = {"name": "测试", "max_hp": 60}
            # 没有 Character 子类
        """)

        loader = PluginLoader(str(tmp_path))
        assert loader.load_plugin(filepath) is False

    def test_load_plugin_invalid_stats_data(self, tmp_path):
        """STATS_DATA 不符合 schema 的插件应被拒绝"""
        filepath = _write_plugin(tmp_path, "bad_stats_plugin.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = "bad_stats"
            STATS_DATA = {"name": 123, "max_hp": "not_int"}

            class BadStatsChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        loader = PluginLoader(str(tmp_path))
        assert loader.load_plugin(filepath) is False

    def test_load_plugin_invalid_role_id(self, tmp_path):
        """ROLE_ID 类型错误的插件应被拒绝"""
        filepath = _write_plugin(tmp_path, "bad_role_plugin.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = 999
            STATS_DATA = {"name": "测试", "max_hp": 60}

            class BadRoleChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        loader = PluginLoader(str(tmp_path))
        assert loader.load_plugin(filepath) is False

    def test_load_plugin_nonexistent_file(self, tmp_path):
        """加载不存在的文件应返回 False"""
        loader = PluginLoader(str(tmp_path))
        assert loader.load_plugin("/nonexistent/path/fake.py") is False

    def test_load_plugin_no_stats_data_backward_compatible(self, tmp_path):
        """没有 STATS_DATA 的插件应向后兼容（使用空字典）"""
        filepath = _write_plugin(tmp_path, "compat_plugin.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = "compat_test"

            class CompatChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        loader = PluginLoader(str(tmp_path))
        assert loader.load_plugin(filepath) is True

        registry = get_character_registry()
        assert "compat_test" in registry.list_available_characters()


class TestPluginLoaderUnloadPlugin:
    """unload_plugin 方法测试"""

    def setup_method(self):
        registry = get_character_registry()
        for role_id in list(registry.list_available_characters()):
            registry.unregister(role_id)

    def test_unload_plugin(self, tmp_path):
        """卸载插件后，注册表中不再包含该角色"""
        filepath = _write_plugin(tmp_path, "unload_test.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = "unload_test"
            STATS_DATA = {"name": "卸载测试", "max_hp": 50}

            class UnloadChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        loader = PluginLoader(str(tmp_path))
        assert loader.load_plugin(filepath) is True

        registry = get_character_registry()
        assert "unload_test" in registry.list_available_characters()

        # 卸载
        assert loader.unload_plugin(filepath) is True
        assert "unload_test" not in registry.list_available_characters()
        assert filepath not in loader.get_loaded_plugins()

    def test_unload_cleans_sys_modules(self, tmp_path):
        """卸载后 sys.modules 中不应包含该模块"""
        filepath = _write_plugin(tmp_path, "sysmod_test.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = "sysmod_test"
            STATS_DATA = {"name": "模块测试", "max_hp": 50}

            class SysmodChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        loader = PluginLoader(str(tmp_path))
        loader.load_plugin(filepath)

        # 确认模块已加载到 sys.modules
        module_name = "plugin_sysmod_test"
        assert module_name in sys.modules

        # 卸载后应从 sys.modules 移除
        loader.unload_plugin(filepath)
        assert module_name not in sys.modules

    def test_unload_nonexistent(self, tmp_path):
        """卸载未加载的插件应返回 False"""
        loader = PluginLoader(str(tmp_path))
        assert loader.unload_plugin("/nonexistent.py") is False


class TestPluginLoaderReloadPlugin:
    """reload_plugin 方法测试"""

    def setup_method(self):
        registry = get_character_registry()
        for role_id in list(registry.list_available_characters()):
            registry.unregister(role_id)

    def test_reload_plugin(self, tmp_path):
        """重载插件后应使用新版本"""
        filepath = _write_plugin(tmp_path, "reload_test.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = "reload_test"
            STATS_DATA = {"name": "版本1", "max_hp": 50}

            class ReloadChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        loader = PluginLoader(str(tmp_path))
        loader.load_plugin(filepath)

        registry = get_character_registry()
        meta = registry.get_metadata("reload_test")
        assert meta["display_name"] == "版本1"

        # 修改文件并重载
        _write_plugin(tmp_path, "reload_test.py", """\
            import sys, os
            sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))
            from core.character import Character

            ROLE_ID = "reload_test"
            STATS_DATA = {"name": "版本2", "max_hp": 60}

            class ReloadChar(Character):
                def use_skill(self, skill_name: str):
                    pass
        """)

        assert loader.reload_plugin(filepath) is True
        meta = registry.get_metadata("reload_test")
        assert meta["display_name"] == "版本2"


class TestPluginLoaderDiscoverPlugins:
    """discover_plugins 方法测试"""

    def test_discover_in_directory(self, tmp_path):
        """应发现目录中的 Python 文件"""
        _write_plugin(tmp_path, "plugin_a.py", "# empty")
        _write_plugin(tmp_path, "plugin_b.py", "# empty")
        _write_plugin(tmp_path, "_private.py", "# 应被忽略")

        loader = PluginLoader(str(tmp_path))
        plugins = loader.discover_plugins()
        basenames = [os.path.basename(p) for p in plugins if not p.startswith("entrypoint:")]

        assert "plugin_a.py" in basenames
        assert "plugin_b.py" in basenames
        assert "_private.py" not in basenames

    def test_discover_nonexistent_dir(self):
        """不存在的目录应返回空列表（不报错）"""
        loader = PluginLoader("/nonexistent/dir")
        plugins = loader.discover_plugins()
        # 可能包含 entry_points 但不应有文件
        file_plugins = [p for p in plugins if not p.startswith("entrypoint:")]
        assert file_plugins == []
