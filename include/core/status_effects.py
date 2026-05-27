# -*- coding: utf-8 -*-
from dataclasses import dataclass
from typing import Literal

AccumulationBucket = Literal["resource", "modifier"]


@dataclass(frozen=True)
class ControlDefinition:
    name: str
    blocks_action: bool = True
    dispellable: bool = True
    category: str = "control"


CONTROL_DEFINITIONS = {
    "护盾": ControlDefinition("护盾", blocks_action=False, category="shield"),
    "风阵": ControlDefinition("风阵", blocks_action=False, category="targeting_rule"),
    "火阵": ControlDefinition("火阵", blocks_action=False, category="turn_damage"),
    "飞镰": ControlDefinition("飞镰", blocks_action=False, category="binding_marker"),
    "瘟阵": ControlDefinition("瘟阵"),
    "灰阵": ControlDefinition("灰阵"),
    "烟雾弹": ControlDefinition("烟雾弹"),
    "纱袋": ControlDefinition("纱袋"),
    "教训你": ControlDefinition("教训你"),
    "高压电池": ControlDefinition("高压电池"),
    "亮瞎你": ControlDefinition("亮瞎你"),
    "死亡之门": ControlDefinition("死亡之门"),
    "六星法阵": ControlDefinition("六星法阵"),
    "铁索覆身": ControlDefinition("铁索覆身"),
    "挥镰": ControlDefinition("挥镰"),
    "lightning_strike": ControlDefinition("lightning_strike"),
}

NON_BLOCKING_CONTROL_NAMES = frozenset(
    name
    for name, definition in CONTROL_DEFINITIONS.items()
    if not definition.blocks_action
)

RESOURCE_ACCUMULATIONS = frozenset({"狼", "熊", "空投", "电池", "光盘"})
MODIFIER_ACCUMULATIONS = frozenset({"攻击强化", "易伤", "立盾"})


def get_control_definition(control_name: str) -> ControlDefinition:
    return CONTROL_DEFINITIONS.get(control_name, ControlDefinition(control_name))


def control_blocks_action(control_name: str) -> bool:
    return get_control_definition(control_name).blocks_action


def control_is_non_blocking(control_name: str) -> bool:
    return not control_blocks_action(control_name)


def accumulation_bucket(effect: str) -> AccumulationBucket:
    if effect in MODIFIER_ACCUMULATIONS:
        return "modifier"
    return "resource"
