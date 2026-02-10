# -*- coding: utf-8 -*-
"""
test_plugin_interface.py - 插件接口校验测试
验证 CharacterPlugin ABC 和 validate_plugin_module 函数
"""

import types

from core.character import Character
from core.plugin_interface import CharacterPlugin, validate_plugin_module


class _ValidCharacter(Character):
    """测试用的合格角色类"""
    def use_skill(self, skill_name: str):
        pass


def _make_module(**attrs):
    """创建模拟模块对象"""
    module = types.ModuleType("test_plugin_module")
    for k, v in attrs.items():
        setattr(module, k, v)
    return module


class TestValidatePluginModule:
    """validate_plugin_module 函数测试"""

    def test_valid_module(self):
        """合格插件模块应通过校验"""
        module = _make_module(
            ROLE_ID="test_role",
            STATS_DATA={"name": "测试角色", "max_hp": 60},
            ValidCharacter=_ValidCharacter,
        )
        assert validate_plugin_module(module) is None

    def test_missing_character_class(self):
        """缺少 Character 子类的模块应校验失败"""
        module = _make_module(
            ROLE_ID="test_role",
            STATS_DATA={"name": "测试", "max_hp": 60},
        )
        error = validate_plugin_module(module)
        assert error is not None
        assert "Character 子类" in error

    def test_invalid_role_id_type(self):
        """ROLE_ID 不是字符串时应校验失败"""
        module = _make_module(
            ROLE_ID=123,
            STATS_DATA={"name": "测试", "max_hp": 60},
            ValidCharacter=_ValidCharacter,
        )
        error = validate_plugin_module(module)
        assert error is not None
        assert "ROLE_ID" in error

    def test_empty_role_id(self):
        """ROLE_ID 为空字符串时应校验失败"""
        module = _make_module(
            ROLE_ID="  ",
            STATS_DATA={"name": "测试", "max_hp": 60},
            ValidCharacter=_ValidCharacter,
        )
        error = validate_plugin_module(module)
        assert error is not None
        assert "ROLE_ID" in error

    def test_invalid_stats_data_type(self):
        """STATS_DATA 不是字典时应校验失败"""
        module = _make_module(
            ROLE_ID="test_role",
            STATS_DATA="not a dict",
            ValidCharacter=_ValidCharacter,
        )
        error = validate_plugin_module(module)
        assert error is not None
        assert "STATS_DATA" in error

    def test_no_role_id_still_passes(self):
        """未定义 ROLE_ID 时（向后兼容），校验应通过"""
        module = _make_module(
            STATS_DATA={"name": "测试角色", "max_hp": 60},
            ValidCharacter=_ValidCharacter,
        )
        assert validate_plugin_module(module) is None

    def test_no_stats_data_still_passes(self):
        """未定义 STATS_DATA 时（向后兼容），校验应通过"""
        module = _make_module(
            ROLE_ID="test_role",
            ValidCharacter=_ValidCharacter,
        )
        assert validate_plugin_module(module) is None


class TestCharacterPluginABC:
    """CharacterPlugin 抽象基类测试"""

    def test_cannot_instantiate_abc(self):
        """CharacterPlugin 本身不能被实例化"""
        try:
            CharacterPlugin()
            assert False, "应该抛出 TypeError"
        except TypeError:
            pass

    def test_concrete_subclass(self):
        """正确实现的子类可以实例化"""

        class MyPlugin(CharacterPlugin):
            ROLE_ID = "my_plugin"
            STATS_DATA = {"name": "test", "max_hp": 50}

            @classmethod
            def get_character_class(cls):
                return _ValidCharacter

        plugin = MyPlugin()
        assert plugin.ROLE_ID == "my_plugin"
        assert MyPlugin.get_character_class() == _ValidCharacter
