# -*- coding: utf-8 -*-
"""结构化动作模型，以及旧中文动作字符串的兼容 Adapter。"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional


_DISABLED_REASON_PREFIXES = (
    "CD:",
    "无次数",
    "条件不足",
    "历史不足",
    "上上回合有控制",
    "积累不足:",
    "无有效目标",
    "不可用",
    "无铁索目标",
    "需隐身",
    "电池不足:",
    "无机器人",
    "机器人模式不可用",
    "激活中",
    "无死亡之门",
    "无飞镰目标",
    "无飞镰斩",
)


class ActionKind(str, Enum):
    SKILL = "skill"
    BEHAVIOR = "behavior"
    INTERACTION = "interaction"


class TargetMode(str, Enum):
    NONE = "none"
    SINGLE = "single"
    MULTI = "multi"
    AUTOMATIC = "automatic"


@dataclass(frozen=True)
class ActionOption:
    """后端对前端公开的动作选项。"""

    action_id: str
    kind: ActionKind
    name: str
    label: str
    enabled: bool = True
    disabled_reason: Optional[str] = None
    legacy_action: Optional[str] = None
    target_mode: TargetMode = TargetMode.NONE

    def to_dict(self, index: int) -> dict:
        return {
            "index": index,
            "id": self.action_id,
            "kind": self.kind.value,
            "name": self.name,
            "label": self.label,
            "enabled": self.enabled,
            "disabled_reason": self.disabled_reason,
            "target_mode": self.target_mode.value,
            "requires_target": self.target_mode == TargetMode.SINGLE,
            "auto_multi": self.target_mode in {TargetMode.MULTI, TargetMode.AUTOMATIC},
            # 兼容现有 CLI 和网络客户端。
            "action": self.legacy_action or self.label,
            "is_unavailable": not self.enabled,
        }


@dataclass(frozen=True)
class ActionResult:
    """动作执行结果；传输 Adapter 只负责广播 message。"""

    success: bool
    message: str
    retry: bool = False


def action_option_from_legacy(action: str) -> ActionOption:
    """将现有展示字符串转换成结构化动作。"""
    if action.startswith("技能:"):
        raw_name = action.removeprefix("技能:")
        name, reason = _split_reason(raw_name)
        return ActionOption(
            action_id=f"skill:{name}",
            kind=ActionKind.SKILL,
            name=name,
            label=name,
            enabled=reason is None,
            disabled_reason=reason,
            legacy_action=action,
        )

    if action.startswith("行为:"):
        name = action.removeprefix("行为:")
        return ActionOption(
            action_id=f"behavior:{name}",
            kind=ActionKind.BEHAVIOR,
            name=name,
            label=name,
            legacy_action=action,
        )

    return ActionOption(
        action_id=f"interaction:{action}",
        kind=ActionKind.INTERACTION,
        name=action,
        label=action,
        legacy_action=action,
    )


def _split_reason(value: str):
    if value.endswith(")") and "(" in value:
        name, reason = value.rsplit("(", 1)
        reason = reason[:-1]
        if reason.startswith(_DISABLED_REASON_PREFIXES):
            return name, reason
    return value, None
