# -*- coding: utf-8 -*-
"""对局角色名册与地块状态的唯一写入 Module。"""

import random
from typing import Iterable, List, Optional, Sequence

from core.character import Character


class BattleRoster:
    def __init__(self, characters: Iterable[Character]):
        self._all = list(characters)
        self._alive = [character for character in self._all if character.is_alive()]

    @property
    def all(self) -> Sequence[Character]:
        return tuple(self._all)

    @property
    def alive(self) -> Sequence[Character]:
        return tuple(self._alive)

    def replace(self, characters: Iterable[Character]):
        self._all = list(characters)
        self.refresh_alive()

    def register(self, character: Character):
        if character not in self._all:
            self._all.append(character)
        if character.is_alive() and character not in self._alive:
            self._alive.append(character)

    def refresh_alive(self):
        self._alive = [character for character in self._all if character.is_alive()]

    def was_alive(self) -> set:
        return set(self._alive)


class BoardState:
    def __init__(self, roster: BattleRoster):
        self.roster = roster

    def initialize(self):
        for character in self.roster.all:
            character.block_id = id(character)
        self.rebuild_nearby_cache()

    def move(self, character: Character, block_id: int) -> bool:
        if character.block_id == block_id:
            return False
        character.block_id = block_id
        self.rebuild_nearby_cache()
        return True

    def rebuild_nearby_cache(self):
        blocks = {}
        for character in self.roster.all:
            blocks.setdefault(character.block_id, []).append(character)
        for character in self.roster.all:
            character.nearby_characters = blocks[character.block_id].copy()

    def members(self, block_id: int) -> List[Character]:
        return [
            character for character in self.roster.all if character.block_id == block_id
        ]

    def count(self, block_id: int) -> int:
        return len(self.members(block_id))

    def random_empty_block(self, reserved: Optional[Iterable[int]] = None) -> int:
        occupied = {character.block_id for character in self.roster.all}
        occupied.update(reserved or ())
        block_id = random.randint(1, 2**31 - 1)
        while block_id in occupied:
            block_id = random.randint(1, 2**31 - 1)
        return block_id
