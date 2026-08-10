# -*- coding: utf-8 -*-
"""对局角色名册与地块状态的唯一写入 Module。"""

import random
from typing import Callable, Iterable, List, Optional, Sequence

from core.character import Character


class BattleRoster:
    def __init__(self, characters: Iterable[Character]):
        self._all = list(characters)
        self._alive = [character for character in self._all if character.is_alive()]
        self._membership_change_handler: Optional[
            Callable[[Sequence[Character], Sequence[Character]], None]
        ] = None

    @property
    def all(self) -> Sequence[Character]:
        return tuple(self._all)

    @property
    def alive(self) -> Sequence[Character]:
        return tuple(self._alive)

    def replace(self, characters: Iterable[Character]) -> None:
        previous = tuple(self._all)
        self._all = list(characters)
        self.refresh_alive()
        self._notify_membership_change(previous)

    def register(self, character: Character) -> None:
        previous = tuple(self._all)
        added = False
        if character not in self._all:
            self._all.append(character)
            added = True
        if character.is_alive() and character not in self._alive:
            self._alive.append(character)
        if added:
            self._notify_membership_change(previous)

    def refresh_alive(self):
        self._alive = [character for character in self._all if character.is_alive()]

    def was_alive(self) -> set:
        return set(self._alive)

    def _set_membership_change_handler(
        self,
        handler: Callable[[Sequence[Character], Sequence[Character]], None],
    ) -> None:
        self._membership_change_handler = handler

    def _notify_membership_change(self, previous: Sequence[Character]) -> None:
        if self._membership_change_handler is not None:
            self._membership_change_handler(previous, self.all)


class BoardState:
    def __init__(self, roster: BattleRoster):
        self.roster = roster
        self.roster._set_membership_change_handler(self._sync_roster_membership)
        self._sync_roster_membership((), self.roster.all)

    def initialize(self):
        for character in self.roster.all:
            self._bind_character(character)
            self._write_block_id(character, id(character))
        self.rebuild_nearby_cache()

    def replace(self, characters: Iterable[Character]) -> None:
        """替换角色名册并原子地重建地块状态。"""
        self.roster.replace(characters)
        self.initialize()

    def register(
        self,
        character: Character,
        block_id: Optional[int] = None,
    ) -> None:
        """将角色注册到对局，并同步其地块与附近角色缓存。"""
        was_registered = character in self.roster.all
        if block_id is not None:
            self._write_block_id(character, block_id)
        self.roster.register(character)
        if was_registered:
            self._bind_character(character)
            self.rebuild_nearby_cache()

    def move(self, character: Character, block_id: int) -> bool:
        if character.block_id == block_id:
            return False
        self._write_block_id(character, block_id)
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

    def _sync_roster_membership(
        self,
        previous: Sequence[Character],
        current: Sequence[Character],
    ) -> None:
        previous_set = set(previous)
        current_set = set(current)
        for character in previous_set - current_set:
            character._bind_block_move_handler(None)
        for character in current:
            self._bind_character(character)
        self.rebuild_nearby_cache()

    def _bind_character(self, character: Character) -> None:
        character._bind_block_move_handler(self.move)

    @staticmethod
    def _write_block_id(character: Character, block_id: int) -> None:
        character._set_block_id_from_battle(block_id)
