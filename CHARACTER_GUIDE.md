# 角色扩展指南 (Character Extension Guide)

本文档说明如何向游戏添加新角色。

## 概述

游戏使用 CharacterFactory 和 CharacterRegistry 系统来管理角色。添加新角色只需3个简单步骤。

## 添加新角色的步骤

### 1. 创建角色类

在 `include/` 目录下创建新的角色文件，例如 `Archer.py`:

```python
# -*- coding: utf-8 -*-
# Archer.py
from typing import Optional
from Character import Character
from Skill import Skill

class Archer(Character):
    def __init__(self, name: str = "弓箭手"):
        super().__init__(name, max_hp=50, control={}, stealth=0)
        self._initialize_skills()
        # 添加角色特有属性
        self.arrow_count = 10
    
    def _initialize_skills(self):
        """初始化角色技能"""
        # 技能1：普通射击
        normal_shot = Skill("普通射击", cooldown=0)
        normal_shot.set_effect(self._normal_shot_effect)
        self.add_or_replace_skill(normal_shot)
        
        # 技能2：穿透箭
        pierce_arrow = Skill("穿透箭", cooldown=2)
        pierce_arrow.set_effect(self._pierce_arrow_effect)
        self.add_or_replace_skill(pierce_arrow)
    
    def use_skill(self, skill_name: str):
        self.use_skill_on_target(skill_name, self)
    
    def use_skill_on_target(self, skill_name: str, target: Character):
        skill = self.get_skill(skill_name)
        if not skill:
            print(f"{self.name} 没有技能: {skill_name}")
            return
        
        if not skill.is_available():
            print(f"技能 {skill_name} 在冷却中 (CD:{skill.get_cooldown()})")
            return
        
        # 可以添加特殊条件检查
        if skill_name == "穿透箭" and self.arrow_count < 3:
            print(f"穿透箭需要至少3支箭，当前只有{self.arrow_count}支")
            return
        
        success = skill.execute_with_target(self, target)
        if success:
            print(f"{self.name} 对 {target.get_name()} 使用了 {skill_name}")
    
    def _normal_shot_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        target.take_damage(5)
        return True
    
    def _pierce_arrow_effect(self, caster: Character, target: Optional[Character]) -> bool:
        if not target:
            return False
        if self.arrow_count < 3:
            return False
        self.arrow_count -= 3
        target.take_damage(15)
        target.add_imprint("穿透伤", 1)
        print(f"{self.name} 消耗3支箭，剩余{self.arrow_count}支")
        return True

# 角色技能数据（用于文档和UI显示）
ARCHER_SKILLS_DATA = {
    "普通射击": {
        "name": "普通射击",
        "cooldown": 0,
        "damage": 5,
        "effect": "基础远程攻击",
        "range": "远程"
    },
    "穿透箭": {
        "name": "穿透箭",
        "cooldown": 2,
        "damage": 15,
        "effect": "消耗3支箭，造成穿透伤害并添加印记",
        "requirement": "需要至少3支箭",
        "range": "远程"
    }
}

# 角色基础数据
ARCHER_STATS_DATA = {
    "name": "弓箭手",
    "max_hp": 50,
    "control": {},
    "stealth": 0,
    "role_type": "远程输出",
    "description": "擅长远程攻击的灵活角色"
}
```

### 2. 注册角色到系统

在 `character_init.py` 中注册新角色:

```python
# 在文件开头添加导入
from Archer import Archer, ARCHER_STATS_DATA

# 在 initialize_characters() 函数中添加注册代码
def initialize_characters():
    """初始化并注册所有角色"""
    
    # ... 现有角色注册代码 ...
    
    # 注册弓箭手
    register_character(
        role_id="archer",
        character_class=Archer,
        display_name=ARCHER_STATS_DATA.get("name", "弓箭手"),
        description=ARCHER_STATS_DATA.get("description", ""),
        stats=ARCHER_STATS_DATA
    )
```

### 3. 测试新角色

创建测试脚本验证新角色:

```python
import character_init
from CharacterFactory import get_character_factory
from main import Game

factory = get_character_factory()

# 测试创建弓箭手
archer = factory.create("archer", "测试弓箭手")
print(f"创建角色: {archer.name}, HP: {archer.max_hp}")

# 测试游戏
characters = [
    factory.create("archer", "弓箭手1"),
    factory.create("knight", "骑士1"),
    factory.create("summoner", "召唤师1")
]

game = Game(characters)
print(f"游戏角色: {[c.name for c in game.all_characters]}")
```

## 高级功能

### 添加角色特殊事件处理

如果角色需要在特定事件时触发逻辑（如死亡、复活等），可以重写以下方法:

```python
class Archer(Character):
    # ... 其他代码 ...
    
    def on_turn_start(self):
        """每回合开始时调用"""
        super().on_turn_start()
        # 每回合恢复1支箭
        if self.arrow_count < 10:
            self.arrow_count += 1
            print(f"{self.name} 补充了1支箭，当前{self.arrow_count}支")
    
    def on_destroy(self):
        """角色死亡时调用"""
        super().on_destroy()
        print(f"{self.name} 的箭散落一地...")
    
    def reset_battle_round(self):
        """重置战斗回合状态"""
        self.arrow_count = 10
        print(f"{self.name} 准备就绪，箭已装满")
```

### 添加角色专属行为

可以重写 `on_behavior_change` 方法添加角色专属的行为提示:

```python
def on_behavior_change(self, old_behavior, new_behavior):
    """行为改变时的回调"""
    if new_behavior == BehaviorType.MOVE_CLOSE:
        print(f"{self.name} 悄悄靠近目标！")
    elif new_behavior == BehaviorType.MOVE_AWAY:
        print(f"{self.name} 拉开距离寻找射击位置！")
```

## 注意事项

1. **继承 Character 基类**: 所有角色必须继承 `Character` 类
2. **实现必要方法**: 必须实现 `use_skill()` 和 `use_skill_on_target()` 方法
3. **技能效果函数**: 技能效果函数签名必须是 `(caster: Character, target: Optional[Character]) -> bool`
4. **唯一 role_id**: 每个角色的 `role_id` 必须唯一
5. **数据导出**: 提供 `SKILLS_DATA` 和 `STATS_DATA` 字典便于UI显示

## 角色平衡建议

- **生命值范围**: 建议 40-80
- **技能冷却**: 强力技能建议 2-3 回合
- **伤害平衡**: 无冷却技能 3-6 伤害，有冷却技能 10-30 伤害
- **特殊机制**: 避免过于复杂的条件判断，保持游戏流畅

## 示例角色设计

查看现有角色了解更多设计模式:
- `Knight.py` - 防御型角色，带状态回退机制
- `Summoner.py` - 累积型角色，需要积攒资源
- `Swordsman.py` - 连击型角色，印记触发机制

## 调试技巧

使用以下代码快速测试新角色:

```python
import character_init
from CharacterFactory import get_character_factory

factory = get_character_factory()
char = factory.create("your_role_id", "测试名称")

# 测试技能
print("可用技能:", list(char.skills.keys()))

# 测试属性
print(f"HP: {char.max_hp}")
print(f"技能数量: {len(char.skills)}")
```

## 问题排查

如果遇到问题:
1. 检查是否在 `character_init.py` 中正确注册
2. 确认 `role_id` 拼写正确
3. 验证技能效果函数返回值为 bool
4. 检查是否调用了 `super().__init__()`

## 进一步扩展

未来可以考虑:
- 从 JSON/YAML 文件加载角色配置
- 添加角色装备系统
- 实现角色升级机制
- 支持角色技能树
