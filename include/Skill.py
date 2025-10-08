"""
Skill 类
- 表示一个技能的基本信息（名字、冷却）
- 提供虚拟的 execute 接口，允许传入回调或在子类中重写以实现具体效果
- 提供拷贝语义

设计注意：
- 技能效果不直接修改目标对象（因为这需要引用 Character 类型），
  execute 的具体实现可通过传入回调或在更高层调用 Character 的方法来完成。

改进点：
- 添加了技能效果回调机制，允许技能执行实际游戏逻辑
- 增加了施法者和目标参数，使技能能够影响具体角色
"""

from typing import Callable, Optional

from Character import Character


class Skill:
    def __init__(self, name: str = "", cooldown: int = 0,
                 effect: Optional[Callable[[Character, Optional[Character]], bool]] = None):
        self.name = name
        self.base_cooldown = max(0, cooldown)
        self.cooldown = 0

        # 技能效果回调函数：参数为施法者和可选目标，返回是否施放成功
        self.effect = effect

    # 获取技能名
    def get_name(self) -> str:
        return self.name

    # 获取基础冷却
    def get_base_cooldown(self) -> int:
        return self.base_cooldown

    # 获取当前冷却
    def get_cooldown(self) -> int:
        return self.cooldown

    # 设置基础冷却，边界检查确保冷却 >= 0
    def set_base_cooldown(self, cd: int):
        self.base_cooldown = max(0, cd)

    # 设置当前冷却
    def set_cooldown(self, cd: int):
        self.cooldown = max(0, cd)

    # 减少冷却（如果大于0则减1）；返回是否发生了变化
    def reduce_cooldown(self) -> bool:
        if self.cooldown > 0:
            self.cooldown -= 1
            return True
        return False

    # 检查是否可用（冷却为0）
    def is_available(self) -> bool:
        return self.cooldown == 0

    # 设置技能效果回调
    def set_effect(self, effect: Callable[[Character, Optional[Character]], bool]):
        self.effect = effect

    # 执行技能 - 基础版本，需要施法者参数
    # 返回是否成功施放
    def execute(self, caster: Character) -> bool:
        return self.execute_with_target(caster, None)

    # 执行技能 - 完整版本，包含施法者和目标
    # 返回是否成功施放
    def execute_with_target(self, caster: Character, target: Optional[Character]) -> bool:
        if not self.is_available():
            print(f"技能 {self.name} 在冷却中 (CD:{self.cooldown})")
            return False

        success = True

        # 如果有自定义效果回调，执行它
        if self.effect:
            success = self.effect(caster, target)
        else:
            # 默认效果：只是打印信息
            print(f"{caster.get_name()} 施放了技能: {self.name}", end="")
            if target:
                print(f" 目标: {target.get_name()}", end="")
            print()

        # 只有施放成功才进入冷却
        if success:
            self.cooldown = self.base_cooldown

        return success
