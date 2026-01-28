# -*- coding: utf-8 -*-
"""
Summon 派生类
- 表示召唤物，行为类似于原先的 Summon 类
- 可以重写 on_summon/on_destroy/take_damage 等行为

改进点：
- 改进了摧毁检测逻辑，确保只在状态变化时触发 on_destroy
- 支持带目标的技能施放
"""

from Character import Character


class Summon(Character):
    def __init__(self, summon_name: str = "", max_health: int = 0, control: dict = None, stlth: int = 0):
        super().__init__(summon_name, max_health, control, stlth)

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
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return

        ok = skill.execute_with_target(self, target)
        if ok:
            print(f"{self.name} 对 {target.get_name()} 施放了技能 {skill_name}")

    def take_damage(self, damage: int):
        was_alive = self.is_alive()
        super().take_damage(damage)
        if was_alive and self.is_destroyed():
            print(f"召唤物 {self.name} 被摧毁！")

    def on_summon(self):
        print(f"{self.name} 被召唤到战场（Summon::on_summon）！")

    def on_destroy(self):
        print(f"{self.name} 从战场上消失（Summon::on_destroy）！")
