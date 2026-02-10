# -*- coding: utf-8 -*-
"""
PluginSchema - 插件 STATS_DATA 结构校验

对插件的 STATS_DATA 做运行时模式校验，确保包含必要字段且类型正确。
使用自定义校验（不依赖 pydantic），保持零外部依赖。

STATS_DATA 必须包含的字段:
  - name (str): 角色名称
  - max_hp (int): 最大生命值，必须 > 0

STATS_DATA 可选字段:
  - description (str): 角色描述
  - role_type (str): 角色类型
  - control (dict): 控制效果
  - stealth (int): 潜行值
"""

from typing import Dict, List, Optional, Tuple


# 必须字段定义: (字段名, 期望类型, 描述)
_REQUIRED_FIELDS: List[Tuple[str, type, str]] = [
    ("name", str, "角色名称"),
    ("max_hp", int, "最大生命值"),
]

# 可选字段定义: (字段名, 期望类型, 描述)
_OPTIONAL_FIELDS: List[Tuple[str, type, str]] = [
    ("description", str, "角色描述"),
    ("role_type", str, "角色类型"),
    ("control", dict, "控制效果"),
    ("stealth", int, "潜行值"),
]


def validate_stats_data(stats_data: dict, filepath: str = "<unknown>") -> Optional[str]:
    """
    校验 STATS_DATA 字典是否符合模式要求。

    Args:
        stats_data: 待校验的 STATS_DATA 字典
        filepath: 插件文件路径（用于错误信息）

    Returns:
        None 如果校验通过，否则返回错误信息字符串
    """
    if not isinstance(stats_data, dict):
        return f"插件 {filepath} 的 STATS_DATA 必须是字典类型，当前类型: {type(stats_data).__name__}"

    errors = []

    # 检查必须字段
    for field_name, expected_type, description in _REQUIRED_FIELDS:
        if field_name not in stats_data:
            errors.append(f"缺少必须字段 '{field_name}' ({description})")
        elif not isinstance(stats_data[field_name], expected_type):
            errors.append(
                f"字段 '{field_name}' ({description}) 类型错误: "
                f"期望 {expected_type.__name__}，实际 {type(stats_data[field_name]).__name__}"
            )

    # 检查 max_hp 正值
    if "max_hp" in stats_data and isinstance(stats_data["max_hp"], int):
        if stats_data["max_hp"] <= 0:
            errors.append(f"字段 'max_hp' 必须大于 0，当前值: {stats_data['max_hp']}")

    # 检查可选字段类型（存在时才检查）
    for field_name, expected_type, description in _OPTIONAL_FIELDS:
        if field_name in stats_data and not isinstance(stats_data[field_name], expected_type):
            errors.append(
                f"可选字段 '{field_name}' ({description}) 类型错误: "
                f"期望 {expected_type.__name__}，实际 {type(stats_data[field_name]).__name__}"
            )

    if errors:
        error_list = "; ".join(errors)
        return f"插件 {filepath} 的 STATS_DATA 校验失败: {error_list}"

    return None
