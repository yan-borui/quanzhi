# -*- coding: utf-8 -*-
"""
test_plugin_schema.py - STATS_DATA 模式校验测试
验证 validate_stats_data 函数的正向和反向测试
"""

from core.plugin_schema import validate_stats_data


class TestValidateStatsData:
    """validate_stats_data 函数测试"""

    def test_valid_full_stats(self):
        """完整且合格的 STATS_DATA 应通过校验"""
        stats = {
            "name": "测试角色",
            "max_hp": 60,
            "description": "一个测试角色",
            "role_type": "测试",
            "control": {},
            "stealth": 0,
        }
        assert validate_stats_data(stats) is None

    def test_valid_minimal_stats(self):
        """仅包含必须字段的 STATS_DATA 应通过校验"""
        stats = {"name": "测试角色", "max_hp": 50}
        assert validate_stats_data(stats) is None

    def test_missing_name(self):
        """缺少 name 字段时应校验失败"""
        stats = {"max_hp": 60}
        error = validate_stats_data(stats)
        assert error is not None
        assert "name" in error

    def test_missing_max_hp(self):
        """缺少 max_hp 字段时应校验失败"""
        stats = {"name": "测试角色"}
        error = validate_stats_data(stats)
        assert error is not None
        assert "max_hp" in error

    def test_invalid_name_type(self):
        """name 类型错误时应校验失败"""
        stats = {"name": 123, "max_hp": 60}
        error = validate_stats_data(stats)
        assert error is not None
        assert "name" in error
        assert "类型错误" in error

    def test_invalid_max_hp_type(self):
        """max_hp 类型错误时应校验失败"""
        stats = {"name": "测试", "max_hp": "sixty"}
        error = validate_stats_data(stats)
        assert error is not None
        assert "max_hp" in error

    def test_zero_max_hp(self):
        """max_hp 为 0 时应校验失败"""
        stats = {"name": "测试", "max_hp": 0}
        error = validate_stats_data(stats)
        assert error is not None
        assert "max_hp" in error

    def test_negative_max_hp(self):
        """max_hp 为负值时应校验失败"""
        stats = {"name": "测试", "max_hp": -10}
        error = validate_stats_data(stats)
        assert error is not None
        assert "max_hp" in error

    def test_invalid_optional_field_type(self):
        """可选字段类型错误时应校验失败"""
        stats = {"name": "测试", "max_hp": 60, "description": 123}
        error = validate_stats_data(stats)
        assert error is not None
        assert "description" in error

    def test_non_dict_input(self):
        """非字典输入应校验失败"""
        error = validate_stats_data("not a dict")
        assert error is not None
        assert "字典类型" in error

    def test_empty_dict(self):
        """空字典应校验失败（缺少必须字段）"""
        error = validate_stats_data({})
        assert error is not None
        assert "name" in error
        assert "max_hp" in error
