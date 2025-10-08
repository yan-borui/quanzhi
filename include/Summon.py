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
    def __init__(self, summon_name: str = "", max_health: int = 0, ctrl: int = 0, stlth: int = 0):
        super().__init__(summon_name, max_health, ctrl, stlth)

    # 子类必须实现的技能释放（此处提供默认示例）
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
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return

        # 执行技能（包含目标信息）
        ok = skill.execute_with_target(self, target)
        if ok:
            print(f"{self.name} 对 {target.get_name()} 施放了技能 {skill_name}")

    # 重写 take_damage 实现更安全的摧毁回调
    def take_damage(self, damage: int):
        was_alive = self.is_alive()  # 记录受伤前状态

        super().take_damage(damage)

        # 基类已处理摧毁回调，这里可以添加召唤物特有的逻辑
        if was_alive and self.is_destroyed():
            print(f"召唤物 {self.name} 被摧毁！")

    def on_summon(self):
        print(f"{self.name} 被召唤到战场（Summon::on_summon）！")

    def on_destroy(self):
        print(f"{self.name} 从战场上消失（Summon::on_destroy）！")
