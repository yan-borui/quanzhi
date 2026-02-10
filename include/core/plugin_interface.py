# -*- coding: utf-8 -*-
"""
CharacterPlugin - 角色插件接口（抽象基类）

定义插件必须遵循的规范，确保插件的一致性和兼容性。
插件模块需要满足以下要求：
  - 包含一个继承自 core.character.Character 的角色类
  - 导出 ROLE_ID: str（角色唯一标识）
  - 导出 STATS_DATA: dict（角色元数据，包含 name、max_hp 等字段）
  - 可选：实现 on_register / on_unregister 钩子函数
"""

from abc import ABC, abstractmethod
from typing import Dict, Optional, Type

from core.character import Character


class CharacterPlugin(ABC):
    """
    角色插件抽象基类。

    插件模块可以选择性地定义一个继承此类的插件描述器，
    也可以仅满足模块级别的约定（ROLE_ID、STATS_DATA、Character子类）。

    Attributes:
        ROLE_ID (str): 角色唯一标识符，例如 "knight"、"archer"
        STATS_DATA (dict): 角色元数据字典，应包含 name、max_hp 等字段
    """

    ROLE_ID: str = ""
    STATS_DATA: dict = {}

    @classmethod
    @abstractmethod
    def get_character_class(cls) -> Type[Character]:
        """
        返回该插件提供的角色类（必须继承 Character）。

        Returns:
            Type[Character]: 角色类
        """
        ...

    @classmethod
    def on_register(cls):
        """
        插件被注册到系统时调用的钩子（可选实现）。
        子类可以重写此方法来执行注册后的初始化逻辑。
        """
        pass

    @classmethod
    def on_unregister(cls):
        """
        插件从系统中注销时调用的钩子（可选实现）。
        子类可以重写此方法来执行注销前的清理逻辑。
        """
        pass


def validate_plugin_module(module, filepath: str = "<unknown>") -> Optional[str]:
    """
    校验插件模块是否符合规范。

    检查模块是否包含：
      1. 一个继承 Character 的角色类
      2. ROLE_ID（字符串类型，可选但推荐）
      3. STATS_DATA（字典类型，可选但推荐）

    Args:
        module: 已加载的 Python 模块对象
        filepath: 插件文件路径（用于错误信息）

    Returns:
        None 如果校验通过，否则返回错误信息字符串
    """
    # 检查是否存在 Character 子类
    character_class = None
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if (isinstance(attr, type)
                and issubclass(attr, Character)
                and attr is not Character):
            character_class = attr
            break

    if character_class is None:
        return f"插件 {filepath} 中未找到 Character 子类"

    # 检查 ROLE_ID
    role_id = getattr(module, 'ROLE_ID', None)
    if role_id is not None and not isinstance(role_id, str):
        return f"插件 {filepath} 的 ROLE_ID 必须是字符串类型，当前类型: {type(role_id).__name__}"

    if role_id is not None and len(role_id.strip()) == 0:
        return f"插件 {filepath} 的 ROLE_ID 不能为空字符串"

    # 检查 STATS_DATA
    stats_data = getattr(module, 'STATS_DATA', None)
    if stats_data is not None and not isinstance(stats_data, dict):
        return f"插件 {filepath} 的 STATS_DATA 必须是字典类型，当前类型: {type(stats_data).__name__}"

    return None
