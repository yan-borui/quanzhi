# -*- coding: utf-8 -*-
"""
Player 派生类
- 继承 Character，提供玩家特有的构造与 use_skill 实现（示例）
- 保持与原来 Player 类相似的接口与行为

改进点：
- 支持带目标的技能施放
- 使用更安全的技能访问方式
"""

from Character import Character


class Player(Character):
    def __init__(self, player_name: str = "", max_health: int = 0, control: dict = None, stlth: int = 0):
        super().__init__(player_name, max_health, control, stlth)

    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)

    def use_skill_on_target(self, skill_name: str, target: Character):
        if not skill_name:
            print("技能名为空，无法施放")
            return

        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return

        if not skill.is_available():
            print(f"技能 {skill_name} 正在冷却 (CD:{skill.get_cooldown()})")
            return

        ok = skill.execute(self)
        if ok:
            print(f"{self.name} 对 {target.get_name()} 施放了技能 {skill_name}")
