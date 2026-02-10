# -*- coding: utf-8 -*-
"""
test_entrypoint_plugins.py - entry_points 插件发现测试
验证 discover_plugins 对 entry_points 的支持
"""

from unittest.mock import patch, MagicMock

from factory.plugin_loader import PluginLoader, ENTRYPOINT_GROUP


class TestEntrypointDiscovery:
    """entry_points 发现逻辑测试"""

    def test_discover_includes_entrypoints(self, tmp_path):
        """discover_plugins 应包含 entry_points 中的插件"""
        mock_ep = MagicMock()
        mock_ep.name = "my_plugin"

        mock_eps = MagicMock()
        mock_eps.select.return_value = [mock_ep]

        with patch("factory.plugin_loader.importlib.metadata.entry_points", return_value=mock_eps):
            loader = PluginLoader(str(tmp_path))
            plugins = loader.discover_plugins()

        assert "entrypoint:my_plugin" in plugins

    def test_discover_entrypoints_error_handled(self, tmp_path):
        """entry_points 扫描出错时不应影响文件扫描"""
        with patch("factory.plugin_loader.importlib.metadata.entry_points",
                    side_effect=Exception("mock error")):
            loader = PluginLoader(str(tmp_path))
            # 不应抛出异常
            plugins = loader.discover_plugins()
            assert isinstance(plugins, list)

    def test_load_from_entrypoint_not_found(self, tmp_path):
        """加载不存在的 entry_point 应返回 False"""
        mock_eps = MagicMock()
        mock_eps.select.return_value = []

        with patch("factory.plugin_loader.importlib.metadata.entry_points", return_value=mock_eps):
            loader = PluginLoader(str(tmp_path))
            result = loader.load_plugin("entrypoint:nonexistent")
            assert result is False

    def test_entrypoint_group_constant(self):
        """entry_points 组名应为 'quanzhi.plugins'"""
        assert ENTRYPOINT_GROUP == "quanzhi.plugins"
