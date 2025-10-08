"""
Player 派生类
- 继承 Character，提供玩家特有的构造与 use_skill 实现（示例）
- 保持与原来 Player 类相似的接口与行为

改进点：
- 支持带目标的技能施放
- 使用更安全的技能访问方式
"""

from Character import Character
from Skill import Skill
from typing import Optional


class Player(Character):
    def __init__(self, player_name: str = "", max_health: int = 0, ctrl: int = 0, stlth: int = 0):
        super().__init__(player_name, max_health, ctrl, stlth)
        # 如果玩家需要初始化 accumulations 或通知服务器 imprints，
        # 在高层逻辑中处理（这里仅做本地初始化）

    # 示例性的 use_skill：检查技能存在且可用，然后调用 Skill.execute
    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)  # 默认目标为自己

    # 带目标的技能使用
    def use_skill_on_target(self, skill_name: str, target: Character):
        if not skill_name:
            print("技能名为空，无法施放")
            return

        # 使用更安全的技能访问方式
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return

        if not skill.is_available():
            print(f"技能 {skill_name} 正在冷却 (CD:{skill.get_cooldown()})")
            return

        # 执行技能（包含目标信息）
        ok = skill.execute(self, target)
        if ok:
            print(f"{self.name} 对 {target.get_name()} 施放了技能 {skill_name}")