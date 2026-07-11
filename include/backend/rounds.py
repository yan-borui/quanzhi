# -*- coding: utf-8 -*-
"""显式回合阶段管线。"""

from enum import Enum
from typing import Callable, Dict, Iterable, Tuple


class RoundPhase(str, Enum):
    OPEN = "open"
    CHARACTER_START = "character_start"
    CONTINUOUS_EFFECTS = "continuous_effects"
    DEATH_RESOLUTION = "death_resolution"
    COOLDOWN = "cooldown"
    INITIATIVE = "initiative"


class RoundPipeline:
    def __init__(self, phases: Iterable[Tuple[RoundPhase, Callable[[Dict], None]]]):
        self.phases = list(phases)

    def run(self) -> Dict:
        context: Dict = {"phase_trace": []}
        for phase, handler in self.phases:
            context["phase_trace"].append(phase.value)
            handler(context)
        return context
