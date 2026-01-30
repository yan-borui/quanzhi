# -*- coding: utf-8 -*-
# Behavior.py
from enum import Enum


class BehaviorType(Enum):
    MOVE_CLOSE = "到你身边"
    MOVE_AWAY = "离你远点"
    REMOVE_CONTROL = "解控"
