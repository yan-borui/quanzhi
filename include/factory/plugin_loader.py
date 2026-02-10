# -*- coding: utf-8 -*-
"""
PluginLoader - 插件加载系统
支持从指定目录动态发现和加载角色插件，以及热加载（重新加载已修改的插件）
"""

import importlib
import importlib.util
import os
import sys
import threading
import time
from typing import Dict, List, Optional, Set

from factory.character_factory import get_character_registry, register_character
from core.character import Character


class PluginLoader:
    """角色插件加载器，支持动态发现、加载和热重载"""

    def __init__(self, plugins_dir: str = "plugins"):
        """
        初始化插件加载器

        Args:
            plugins_dir: 插件目录路径（相对或绝对路径）
        """
        self._plugins_dir = os.path.abspath(plugins_dir)
        self._loaded_modules: Dict[str, object] = {}
        self._file_timestamps: Dict[str, float] = {}
        self._watcher_thread: Optional[threading.Thread] = None
        self._watching = False
        self._lock = threading.Lock()

    @property
    def plugins_dir(self) -> str:
        return self._plugins_dir

    def discover_plugins(self) -> List[str]:
        """
        发现插件目录中的所有Python文件

        Returns:
            插件文件路径列表
        """
        if not os.path.isdir(self._plugins_dir):
            return []

        plugins = []
        for filename in sorted(os.listdir(self._plugins_dir)):
            if filename.endswith('.py') and not filename.startswith('_'):
                filepath = os.path.join(self._plugins_dir, filename)
                if os.path.isfile(filepath):
                    plugins.append(filepath)
        return plugins

    def load_plugin(self, filepath: str) -> bool:
        """
        加载单个插件文件

        插件文件需要导出以下内容:
        - 一个继承Character的角色类
        - STATS_DATA 字典（包含角色元数据）
        - ROLE_ID 字符串（角色唯一标识）

        Args:
            filepath: 插件文件路径

        Returns:
            是否加载成功
        """
        if not os.path.isfile(filepath):
            print(f"[插件] 文件不存在: {filepath}")
            return False

        module_name = os.path.splitext(os.path.basename(filepath))[0]
        module_name = f"plugin_{module_name}"

        try:
            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                print(f"[插件] 无法创建模块规格: {filepath}")
                return False

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 查找角色类和元数据
            role_id = getattr(module, 'ROLE_ID', None)
            stats_data = getattr(module, 'STATS_DATA', None)
            character_class = None

            # 自动查找继承Character的类
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (isinstance(attr, type)
                        and issubclass(attr, Character)
                        and attr is not Character):
                    character_class = attr
                    break

            if character_class is None:
                print(f"[插件] {filepath} 中未找到Character子类")
                return False

            if role_id is None:
                # 使用文件名作为role_id
                role_id = os.path.splitext(os.path.basename(filepath))[0]

            if stats_data is None:
                stats_data = {}

            # 注册角色
            register_character(
                role_id=role_id,
                character_class=character_class,
                display_name=stats_data.get("name", role_id),
                description=stats_data.get("description", ""),
                stats=stats_data
            )

            with self._lock:
                self._loaded_modules[filepath] = module
                self._file_timestamps[filepath] = os.path.getmtime(filepath)

            print(f"[插件] 已加载: {role_id} ({filepath})")
            return True

        except Exception as e:
            print(f"[插件] 加载失败 {filepath}: {e}")
            return False

    def load_all_plugins(self) -> int:
        """
        加载所有发现的插件

        Returns:
            成功加载的插件数量
        """
        plugins = self.discover_plugins()
        if not plugins:
            print(f"[插件] 未发现插件文件 (目录: {self._plugins_dir})")
            return 0

        loaded = 0
        for filepath in plugins:
            if self.load_plugin(filepath):
                loaded += 1

        print(f"[插件] 共加载 {loaded}/{len(plugins)} 个插件")
        return loaded

    def reload_plugin(self, filepath: str) -> bool:
        """
        重新加载单个插件（热加载）

        Args:
            filepath: 插件文件路径

        Returns:
            是否重载成功
        """
        with self._lock:
            old_module = self._loaded_modules.get(filepath)

        # 先获取旧的role_id以便注销
        old_role_id = None
        if old_module:
            old_role_id = getattr(old_module, 'ROLE_ID', None)
            if old_role_id is None:
                old_role_id = os.path.splitext(os.path.basename(filepath))[0]

        # 注销旧的注册
        if old_role_id:
            registry = get_character_registry()
            registry.unregister(old_role_id)

        # 重新加载
        return self.load_plugin(filepath)

    def check_and_reload_changed(self) -> List[str]:
        """
        检查插件文件变更并重新加载

        Returns:
            已重新加载的文件路径列表
        """
        reloaded = []

        with self._lock:
            tracked_files = dict(self._file_timestamps)

        # 检查已加载插件的变更
        for filepath, old_mtime in tracked_files.items():
            if not os.path.isfile(filepath):
                continue
            current_mtime = os.path.getmtime(filepath)
            if current_mtime > old_mtime:
                print(f"[热加载] 检测到文件变更: {filepath}")
                if self.reload_plugin(filepath):
                    reloaded.append(filepath)

        # 检查新增插件文件
        current_plugins = set(self.discover_plugins())
        with self._lock:
            loaded_plugins = set(self._loaded_modules.keys())

        new_plugins = current_plugins - loaded_plugins
        for filepath in new_plugins:
            print(f"[热加载] 发现新插件: {filepath}")
            if self.load_plugin(filepath):
                reloaded.append(filepath)

        return reloaded

    def start_watching(self, interval: float = 2.0):
        """
        启动文件监视线程

        Args:
            interval: 检查间隔（秒）
        """
        if self._watching:
            return

        self._watching = True
        self._watcher_thread = threading.Thread(
            target=self._watch_loop,
            args=(interval,),
            daemon=True,
            name="plugin-watcher"
        )
        self._watcher_thread.start()
        print(f"[热加载] 文件监视已启动 (间隔: {interval}s)")

    def stop_watching(self):
        """停止文件监视线程"""
        self._watching = False
        if self._watcher_thread and self._watcher_thread.is_alive():
            self._watcher_thread.join(timeout=5.0)
            if self._watcher_thread.is_alive():
                print("[热加载] 警告: 文件监视线程未能在超时内停止")
        self._watcher_thread = None
        print("[热加载] 文件监视已停止")

    def _watch_loop(self, interval: float):
        """文件监视循环"""
        while self._watching:
            try:
                self.check_and_reload_changed()
            except Exception as e:
                print(f"[热加载] 检查变更时出错: {e}")
            time.sleep(interval)

    def get_loaded_plugins(self) -> List[str]:
        """获取已加载的插件文件列表"""
        with self._lock:
            return list(self._loaded_modules.keys())


# 全局插件加载器实例
_global_plugin_loader: Optional[PluginLoader] = None


def get_plugin_loader() -> PluginLoader:
    """获取全局插件加载器"""
    global _global_plugin_loader
    if _global_plugin_loader is None:
        _global_plugin_loader = PluginLoader()
    return _global_plugin_loader


def init_plugin_loader(plugins_dir: str = "plugins") -> PluginLoader:
    """初始化全局插件加载器"""
    global _global_plugin_loader
    _global_plugin_loader = PluginLoader(plugins_dir)
    return _global_plugin_loader
