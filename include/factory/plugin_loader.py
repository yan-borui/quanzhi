# -*- coding: utf-8 -*-
"""
PluginLoader - 插件加载系统
支持从指定目录动态发现和加载角色插件，以及热加载（重新加载已修改的插件）
支持通过 setuptools entry_points 发现第三方插件（group: "quanzhi.plugins"）
"""

import importlib
import importlib.metadata
import importlib.util
import os
import sys
import threading
import time
import traceback
from typing import Dict, List, Optional, Set, Union

from factory.character_factory import get_character_registry, register_character
from core.character import Character
from core.plugin_interface import validate_plugin_module
from core.plugin_schema import validate_stats_data

# entry_points 组名
ENTRYPOINT_GROUP = "quanzhi.plugins"


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
        发现所有可用插件，包括：
        1. 插件目录中的 Python 文件
        2. 通过 setuptools entry_points 注册的第三方插件

        Returns:
            插件文件路径列表（本地文件为绝对路径，entry_point 为
            "entrypoint:<name>" 格式的标识符）
        """
        plugins = []

        # 1. 文件扫描
        if os.path.isdir(self._plugins_dir):
            for filename in sorted(os.listdir(self._plugins_dir)):
                if filename.endswith('.py') and not filename.startswith('_'):
                    filepath = os.path.join(self._plugins_dir, filename)
                    if os.path.isfile(filepath):
                        plugins.append(filepath)

        # 2. entry_points 扫描
        try:
            eps = importlib.metadata.entry_points()
            # 兼容 Python 3.9+ 和 3.12+ API
            if hasattr(eps, 'select'):
                ep_list = eps.select(group=ENTRYPOINT_GROUP)
            else:
                ep_list = eps.get(ENTRYPOINT_GROUP, [])
            for ep in ep_list:
                plugins.append(f"entrypoint:{ep.name}")
        except Exception as e:
            print(f"[插件] 扫描 entry_points 时出错: {e}")

        return plugins

    def load_plugin(self, filepath: str) -> bool:
        """
        加载单个插件。

        支持以下输入格式:
        - 文件路径: 从文件加载插件模块
        - "entrypoint:<name>": 从 entry_points 加载插件
        - "module:<module_name>": 从已安装的 Python 模块加载

        插件文件需要导出以下内容:
        - 一个继承Character的角色类
        - STATS_DATA 字典（包含角色元数据，需包含 name 和 max_hp）
        - ROLE_ID 字符串（角色唯一标识）

        Args:
            filepath: 插件文件路径、entrypoint 标识或模块名

        Returns:
            是否加载成功
        """
        try:
            # 根据输入类型分别处理
            if filepath.startswith("entrypoint:"):
                return self._load_from_entrypoint(filepath)
            elif filepath.startswith("module:"):
                return self._load_from_module_name(filepath)
            else:
                return self._load_from_file(filepath)
        except Exception as e:
            print(f"[插件] 加载失败 {filepath}: {e}")
            traceback.print_exc()
            return False

    def _load_from_entrypoint(self, identifier: str) -> bool:
        """从 entry_point 加载插件"""
        ep_name = identifier[len("entrypoint:"):]
        try:
            eps = importlib.metadata.entry_points()
            if hasattr(eps, 'select'):
                ep_list = list(eps.select(group=ENTRYPOINT_GROUP, name=ep_name))
            else:
                ep_list = [ep for ep in eps.get(ENTRYPOINT_GROUP, [])
                           if ep.name == ep_name]

            if not ep_list:
                print(f"[插件] 未找到 entry_point: {ep_name}")
                return False

            ep = ep_list[0]
            obj = ep.load()

            # entry_point 可以指向模块或工厂函数
            if isinstance(obj, type) and hasattr(obj, '__module__'):
                module = sys.modules.get(obj.__module__)
                if module:
                    return self._register_module(module, identifier)
            elif hasattr(obj, '__module__'):
                module = sys.modules.get(obj.__module__)
                if module:
                    return self._register_module(module, identifier)

            print(f"[插件] entry_point {ep_name} 加载的对象无法识别")
            return False
        except Exception as e:
            print(f"[插件] 从 entry_point 加载失败 {ep_name}: {e}")
            traceback.print_exc()
            return False

    def _load_from_module_name(self, identifier: str) -> bool:
        """从模块名加载插件"""
        module_name = identifier[len("module:"):]
        try:
            module = importlib.import_module(module_name)
            return self._register_module(module, identifier)
        except Exception as e:
            print(f"[插件] 从模块加载失败 {module_name}: {e}")
            traceback.print_exc()
            return False

    def _load_from_file(self, filepath: str) -> bool:
        """从文件路径加载插件"""
        if not os.path.isfile(filepath):
            print(f"[插件] 文件不存在: {filepath}")
            return False

        module_name = os.path.splitext(os.path.basename(filepath))[0]
        module_name = f"plugin_{module_name}"

        try:
            # 清除字节码缓存，确保重载时读取最新源文件
            try:
                cache_file = importlib.util.cache_from_source(filepath)
                if os.path.exists(cache_file):
                    os.unlink(cache_file)
            except Exception:
                pass

            spec = importlib.util.spec_from_file_location(module_name, filepath)
            if spec is None or spec.loader is None:
                print(f"[插件] 无法创建模块规格: {filepath}")
                return False

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            if not self._register_module(module, filepath):
                # 注册失败时清理 sys.modules
                sys.modules.pop(module_name, None)
                return False

            with self._lock:
                self._file_timestamps[filepath] = os.path.getmtime(filepath)

            return True

        except Exception as e:
            print(f"[插件] 加载文件失败 {filepath}: {e}")
            traceback.print_exc()
            return False

    def _register_module(self, module, filepath: str) -> bool:
        """
        校验并注册插件模块。

        Args:
            module: 已加载的模块对象
            filepath: 插件标识（文件路径或标识符）

        Returns:
            是否注册成功
        """
        # 接口校验
        validation_error = validate_plugin_module(module, filepath)
        if validation_error is not None:
            print(f"[插件] 校验失败: {validation_error}")
            return False

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

        if role_id is None:
            # 使用文件名作为role_id
            basename = os.path.basename(filepath) if os.path.sep in filepath or filepath.endswith('.py') else filepath
            role_id = os.path.splitext(basename)[0]
            print(f"[插件] 警告: {filepath} 未定义 ROLE_ID，使用默认值: {role_id}")

        if stats_data is None:
            stats_data = {}
            print(f"[插件] 警告: {filepath} 未定义 STATS_DATA，使用空字典")
        else:
            # STATS_DATA 模式校验
            validation_error = validate_stats_data(stats_data, filepath)
            if validation_error is not None:
                print(f"[插件] 校验失败: {validation_error}")
                return False

        # 调用可选的 on_register 钩子
        on_register = getattr(module, 'on_register', None)
        if callable(on_register):
            try:
                on_register()
            except Exception as e:
                print(f"[插件] on_register 钩子执行失败 {filepath}: {e}")

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

        print(f"[插件] 已加载: {role_id} ({filepath})")
        return True

    def unload_plugin(self, filepath: str) -> bool:
        """
        卸载已加载的插件。

        从注册表中注销角色，清理模块引用和时间戳记录，
        并尝试从 sys.modules 中移除对应模块。

        Args:
            filepath: 插件文件路径或标识符

        Returns:
            是否卸载成功
        """
        try:
            with self._lock:
                module = self._loaded_modules.get(filepath)

            if module is None:
                print(f"[插件] 未找到已加载的插件: {filepath}")
                return False

            # 获取 role_id
            role_id = getattr(module, 'ROLE_ID', None)
            if role_id is None:
                basename = os.path.basename(filepath) if os.path.sep in filepath or filepath.endswith('.py') else filepath
                role_id = os.path.splitext(basename)[0]

            # 调用可选的 on_unregister 钩子
            on_unregister = getattr(module, 'on_unregister', None)
            if callable(on_unregister):
                try:
                    on_unregister()
                except Exception as e:
                    print(f"[插件] on_unregister 钩子执行失败 {filepath}: {e}")

            # 从注册表注销
            registry = get_character_registry()
            registry.unregister(role_id)
            print(f"[插件] 已注销角色: {role_id}")

            # 清理 sys.modules
            module_name = getattr(module, '__name__', None)
            if module_name and module_name in sys.modules:
                del sys.modules[module_name]
                print(f"[插件] 已从 sys.modules 移除: {module_name}")

            # 清理内部记录
            with self._lock:
                self._loaded_modules.pop(filepath, None)
                self._file_timestamps.pop(filepath, None)

            print(f"[插件] 已卸载: {role_id} ({filepath})")
            return True

        except Exception as e:
            print(f"[插件] 卸载失败 {filepath}: {e}")
            traceback.print_exc()
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

        先卸载旧插件，再重新加载。

        Args:
            filepath: 插件文件路径

        Returns:
            是否重载成功
        """
        try:
            with self._lock:
                is_loaded = filepath in self._loaded_modules

            # 先卸载旧插件
            if is_loaded:
                if not self.unload_plugin(filepath):
                    print(f"[插件] 重载时卸载旧插件失败: {filepath}")

            # 重新加载
            return self.load_plugin(filepath)

        except Exception as e:
            print(f"[插件] 重载失败 {filepath}: {e}")
            traceback.print_exc()
            return False

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
