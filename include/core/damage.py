# -*- coding: utf-8 -*-
"""伤害结算值对象。"""

from dataclasses import dataclass, field
from typing import Any, FrozenSet, Optional


@dataclass(frozen=True)
class DamageEvent:
    amount: int
    source: Optional[Any] = None
    skill_name: Optional[str] = None
    tags: FrozenSet[str] = field(default_factory=frozenset)
