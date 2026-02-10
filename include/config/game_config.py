# -*- coding: utf-8 -*-
"""
GameConfig - 游戏配置系统
提供配置驱动的游戏设置管理，支持从JSON文件加载配置
"""

import json
import os
from typing import Any, Dict, List, Optional


# 默认配置
_DEFAULT_CONFIG = {
    "game": {
        "max_rounds": 100,
        "min_players": 2,
        "max_players": 6,
        "default_characters": ["knight", "summoner", "swordsman"],
        "round_delay": 0.5
    },
    "plugins": {
        "enabled": True,
        "directory": "plugins",
        "auto_load": True,
        "hot_reload": False,
        "watch_interval": 2.0
    }
}


class GameConfig:
    """游戏配置管理器，支持从JSON文件加载和合并配置"""

    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_path: 配置文件路径。如果为None，使用默认配置
        """
        self._config: Dict[str, Any] = {}
        self._config_path: Optional[str] = config_path
        self._load_defaults()
        if config_path:
            self.load_from_file(config_path)

    def _load_defaults(self):
        """加载默认配置"""
        self._config = _deep_copy_dict(_DEFAULT_CONFIG)

    def load_from_file(self, config_path: str) -> bool:
        """
        从JSON文件加载配置，与默认配置合并

        Args:
            config_path: JSON配置文件路径

        Returns:
            是否成功加载
        """
        if not os.path.isfile(config_path):
            print(f"[配置] 配置文件不存在: {config_path}，使用默认配置")
            return False

        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                user_config = json.load(f)
            _deep_merge(self._config, user_config)
            self._config_path = config_path
            print(f"[配置] 已加载配置文件: {config_path}")
            return True
        except (json.JSONDecodeError, IOError) as e:
            print(f"[配置] 加载配置文件失败: {e}，使用默认配置")
            return False

    def reload(self) -> bool:
        """
        重新加载配置文件

        Returns:
            是否成功重新加载
        """
        self._load_defaults()
        if self._config_path:
            return self.load_from_file(self._config_path)
        return True

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        通过点分路径获取配置值

        Args:
            key_path: 配置键路径，如 "game.max_rounds"
            default: 默认值

        Returns:
            配置值
        """
        keys = key_path.split(".")
        value = self._config
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return default
        return value

    def set(self, key_path: str, value: Any):
        """
        通过点分路径设置配置值

        Args:
            key_path: 配置键路径
            value: 配置值
        """
        keys = key_path.split(".")
        config = self._config
        for key in keys[:-1]:
            if key not in config or not isinstance(config[key], dict):
                config[key] = {}
            config = config[key]
        config[keys[-1]] = value

    def get_all(self) -> Dict[str, Any]:
        """获取全部配置的副本"""
        return _deep_copy_dict(self._config)

    # 便捷属性
    @property
    def max_rounds(self) -> int:
        return self.get("game.max_rounds", 100)

    @property
    def min_players(self) -> int:
        return self.get("game.min_players", 2)

    @property
    def max_players(self) -> int:
        return self.get("game.max_players", 6)

    @property
    def default_characters(self) -> List[str]:
        return self.get("game.default_characters", ["knight", "summoner", "swordsman"])

    @property
    def round_delay(self) -> float:
        return self.get("game.round_delay", 0.5)

    @property
    def plugins_enabled(self) -> bool:
        return self.get("plugins.enabled", True)

    @property
    def plugins_directory(self) -> str:
        return self.get("plugins.directory", "plugins")

    @property
    def plugins_auto_load(self) -> bool:
        return self.get("plugins.auto_load", True)

    @property
    def hot_reload_enabled(self) -> bool:
        return self.get("plugins.hot_reload", False)

    @property
    def watch_interval(self) -> float:
        return self.get("plugins.watch_interval", 2.0)


def _deep_copy_dict(d: Dict) -> Dict:
    """深拷贝字典"""
    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            result[k] = _deep_copy_dict(v)
        elif isinstance(v, list):
            result[k] = list(v)
        else:
            result[k] = v
    return result


def _deep_merge(base: Dict, override: Dict):
    """将override合并到base中（就地修改base）"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


# 全局配置实例
_global_config: Optional[GameConfig] = None


def get_game_config() -> GameConfig:
    """获取全局游戏配置"""
    global _global_config
    if _global_config is None:
        _global_config = GameConfig()
    return _global_config


def init_game_config(config_path: Optional[str] = None) -> GameConfig:
    """初始化全局游戏配置"""
    global _global_config
    _global_config = GameConfig(config_path)
    return _global_config
