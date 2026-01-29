# 新系统文档

本文档描述了三个新的战斗系统，用于扩展游戏的角色机制。

## 1. 双人判定系统 (DualJudgmentSystem)

### 概述
双人判定系统允许技能的发起方和承受方进行石头剪刀布判定，根据判定结果决定技能是否成功。

### 文件位置
`include/DualJudgmentSystem.py`

### 核心类

#### `JudgmentResult` (枚举)
- `INITIATOR_WIN`: 发起方获胜
- `TARGET_WIN`: 承受方获胜  
- `DRAW`: 平局（会自动重新判定）

#### `DualJudgmentSystem`

### 主要方法

```python
# 执行判定
result = judgment_system.judge(initiator, target, skill_name)

# 注册技能特殊规则（如自动获胜）
auto_win_rule = judgment_system.create_auto_win_rule("initiator")
judgment_system.register_skill_rule("必胜技能", auto_win_rule)

# 创建条件规则
def condition(initiator, target):
    return initiator.get_current_hp() > 30

conditional_rule = judgment_system.create_conditional_rule(condition, JudgmentResult.INITIATOR_WIN)
judgment_system.register_skill_rule("气势压制", conditional_rule)
```

### 使用示例

```python
# 在技能效果中使用判定系统
def skill_with_judgment(caster, target):
    # 获取游戏的判定系统
    judgment_system = game.get_dual_judgment_system()
    
    # 执行判定
    result = judgment_system.judge(caster, target, "忍法地心")
    
    if result == JudgmentResult.INITIATOR_WIN:
        print(f"{caster.get_name()} 判定成功！")
        # 执行技能效果
        target.take_damage(10)
        return True
    else:
        print(f"{target.get_name()} 躲避成功！")
        return False
```

### 应用场景
- **忍者的"忍法地心"**: 需要判定才能找到隐藏的忍者
- **阵鬼的"五彩法阵"**: 需要判定才能造成巨额伤害
- **机械师的"电子眼"**: 可以注册规则让"找"无需判定

---

## 2. 持续效果系统 (ContinuousEffectSystem)

### 概述
持续效果系统管理多回合自动触发的效果，如持续伤害、持续治疗等。效果可以设置移除条件。

### 文件位置
`include/ContinuousEffectSystem.py`

### 核心类

#### `RemovalCondition` (枚举)
- `NEVER`: 永不移除（直到持续时间结束）
- `ON_MOVEMENT`: 移动时移除
- `ON_DAMAGE`: 受到伤害时移除
- `ON_HEAL`: 被治疗时移除
- `ON_CONTROL`: 获得控制效果时移除
- `CUSTOM`: 自定义条件

#### `ContinuousEffect`
表示一个持续效果实例。

#### `ContinuousEffectSystem`
管理所有角色的持续效果。

### 主要方法

```python
# 创建持续效果
effect = ContinuousEffect(
    name="燃烧",
    duration=3,  # 持续3回合
    trigger_func=lambda target: target.take_damage(3),
    removal_condition=RemovalCondition.ON_MOVEMENT,
    description="每回合造成3点伤害，移动时移除"
)

# 添加效果到目标
effect_system.add_effect(target, effect)

# 每回合触发所有效果（在Game.play_round中自动调用）
effect_system.trigger_all_effects(target)

# 检查移除条件（在移动等事件中自动调用）
effect_system.check_and_remove_on_event(target, "movement")

# 手动移除效果
effect_system.remove_effect(target, "燃烧")

# 检查是否有某效果
has_burn = effect_system.has_effect(target, "燃烧")

# 获取效果层数
count = effect_system.get_effect_count(target, "燃烧")
```

### 使用示例

```python
# 魔道学者的"燃烧瓶"技能
def burning_bottle_effect(caster, target):
    effect_system = game.get_continuous_effect_system()
    
    # 创建燃烧效果：持续3回合，每回合3点伤害，可以通过移动移除
    def burn_damage(t):
        print(f"{t.get_name()} 受到燃烧伤害")
        t.take_damage(3)
    
    burn_effect = ContinuousEffect(
        name="燃烧",
        duration=3,
        trigger_func=burn_damage,
        removal_condition=RemovalCondition.ON_MOVEMENT,
        source=caster,
        description="持续燃烧，可移动解除"
    )
    
    effect_system.add_effect(target, burn_effect)
    return True
```

### 集成到游戏循环
持续效果在每回合开始时自动触发（在`Game.play_round()`中）：
```python
# 处理持续效果（在回合开始时触发）
for char in self.all_characters:
    if char.is_alive():
        self.continuous_effect_system.trigger_all_effects(char)
```

移动时自动检查移除条件（在`Game.move_character_to_block()`中）：
```python
# 触发移动事件，检查是否需要移除持续效果
self.continuous_effect_system.check_and_remove_on_event(character, "movement")
```

### 应用场景
- **魔道学者的"燃烧瓶"**: 持续伤害，可以通过移动解除
- **阵鬼的"火阵"**: 持续造成伤害
- **术士的诅咒类技能**: 多回合的持续debuff

---

## 3. 状态绑定系统 (StateBindingSystem)

### 概述
状态绑定系统管理技能效果与特定目标的绑定关系。当对新目标使用同一技能时，自动解除旧目标的状态。

### 文件位置
`include/StateBindingSystem.py`

### 核心类

#### `StateBinding`
表示一个绑定关系。

#### `StateBindingSystem`
管理所有绑定关系。

### 主要方法

```python
# 创建绑定
def on_bind(source, target):
    print(f"{source.get_name()} 锁定了 {target.get_name()}")
    target.add_control("被锁定", 1)

def on_unbind(source, target):
    print(f"{source.get_name()} 解除了对 {target.get_name()} 的锁定")
    target.reduce_control("被锁定", 1)

binding_system.bind_state(
    skill_name="铁索覆身",
    source=caster,
    target=target,
    on_bind=on_bind,
    on_unbind=on_unbind,
    auto_unbind_old=True  # 自动解除旧绑定
)

# 检查是否已绑定
is_bound = binding_system.is_bound(caster, "铁索覆身")

# 获取当前绑定的目标
current_target = binding_system.get_bound_target(caster, "铁索覆身")

# 手动解绑
binding_system.unbind_state(caster, "铁索覆身")

# 获取目标身上的所有绑定
bindings = binding_system.get_target_bindings(target)
```

### 使用示例

```python
# 忍者的"铁索覆身"技能
def iron_chain_effect(caster, target):
    binding_system = game.get_state_binding_system()
    
    # 定义绑定时的效果
    def on_bind(source, target):
        target.add_control("铁索", 1)
        print(f"{target.get_name()} 被铁索束缚")
    
    # 定义解绑时的效果
    def on_unbind(source, target):
        target.reduce_control("铁索", 1)
        print(f"{target.get_name()} 的铁索被解除")
    
    # 创建绑定（如果已有绑定会自动解除旧的）
    binding_system.bind_state(
        skill_name="铁索覆身",
        source=caster,
        target=target,
        on_bind=on_bind,
        on_unbind=on_unbind
    )
    
    return True

# 使用"樱花岁月"或"忍法地心"时解除铁索
def sakura_skill_effect(caster, target):
    binding_system = game.get_state_binding_system()
    
    # 解除自己的铁索绑定
    if binding_system.is_bound(caster, "铁索覆身"):
        binding_system.unbind_state(caster, "铁索覆身")
    
    # 执行其他技能效果
    target.take_damage(12)
    return True
```

### 应用场景
- **忍者的"铁索覆身"**: 对另一人使用时第一个破，使用特定技能时破
- **镰刀工的"飞镰"**: 对另一人使用时第一个破
- **镰刀工的"挥镰"**: 需等对方解后才可对同一人使用，对另一人使用时第一个破

---

## 访问新系统

在Game实例中，可以通过以下方法访问三个系统：

```python
# 在游戏中访问系统
game = Game(characters)

# 双人判定系统
judgment_system = game.get_dual_judgment_system()

# 持续效果系统
effect_system = game.get_continuous_effect_system()

# 状态绑定系统
binding_system = game.get_state_binding_system()
```

在角色的技能实现中，可以通过game引用访问这些系统。如果需要，可以在角色初始化时传入game引用，或者在技能效果函数中作为参数传入。

---

## 向后兼容性

所有三个系统都是**可选的**，不会影响现有角色的功能：

1. **现有角色无需修改**: 骑士、召唤师、剑客等现有角色继续正常工作
2. **系统独立管理**: 新系统通过角色ID独立管理状态，不修改Character基类
3. **零性能影响**: 如果不使用这些系统，它们不会产生任何性能开销

---

## 测试

运行测试脚本验证所有系统功能：

```bash
python3 test_new_systems.py
```

测试涵盖：
- 双人判定系统的正常判定、自动获胜规则和条件规则
- 持续效果系统的效果触发、移除条件和效果叠加
- 状态绑定系统的绑定、切换目标和解绑
- 向后兼容性验证

---

## 实现新角色示例

以下是如何使用新系统实现CSV中的角色：

### 忍者示例

```python
class Ninja(Character):
    def __init__(self, name: str = "忍者", game=None):
        super().__init__(name, max_hp=60, control={}, stealth=0)
        self.game = game
        self._initialize_skills()
    
    def _initialize_skills(self):
        # 樱花岁月: 2CD, 12伤害, 使用时破铁索
        sakura = Skill("樱花岁月", cooldown=2)
        sakura.set_effect(self._sakura_effect)
        self.add_or_replace_skill(sakura)
        
        # 铁索覆身: 0CD, 控制, 对另一人使用时第一个破
        iron_chain = Skill("铁索覆身", cooldown=0)
        iron_chain.set_effect(self._iron_chain_effect)
        self.add_or_replace_skill(iron_chain)
        
        # 忍法地心: 2CD, 需判定找到对方
        earth_jutsu = Skill("忍法地心", cooldown=2)
        earth_jutsu.set_effect(self._earth_jutsu_effect)
        self.add_or_replace_skill(earth_jutsu)
    
    def _sakura_effect(self, caster, target):
        # 解除自己的铁索绑定
        if self.game:
            binding_system = self.game.get_state_binding_system()
            if binding_system.is_bound(self, "铁索覆身"):
                binding_system.unbind_state(self, "铁索覆身")
        
        target.take_damage(12)
        return True
    
    def _iron_chain_effect(self, caster, target):
        if not self.game:
            return False
        
        binding_system = self.game.get_state_binding_system()
        
        def on_bind(source, target):
            target.add_control("铁索", 1)
        
        def on_unbind(source, target):
            target.reduce_control("铁索", 1)
        
        binding_system.bind_state(
            skill_name="铁索覆身",
            source=self,
            target=target,
            on_bind=on_bind,
            on_unbind=on_unbind
        )
        return True
    
    def _earth_jutsu_effect(self, caster, target):
        if not self.game:
            return False
        
        judgment_system = self.game.get_dual_judgment_system()
        result = judgment_system.judge(self, target, "忍法地心")
        
        if result == JudgmentResult.INITIATOR_WIN:
            # 判定成功，给自己添加印记
            self.add_imprint("地心成功", 1)
            return True
        else:
            print("对方躲避成功！")
            return False
```

---

## 注意事项

1. **性能**: 每回合只触发存活角色的持续效果，死亡角色的效果会被自动清理
2. **线程安全**: 当前实现是单线程的，如需多线程需要添加锁
3. **持久化**: 系统状态不会自动保存，如需保存/加载游戏需要额外实现
4. **调试**: 所有系统都有详细的日志输出，便于调试

---

## 未来扩展

这三个系统为未来添加更复杂的角色机制奠定了基础：

1. **技能链**: 可以基于判定系统实现技能连击
2. **Buff/Debuff**: 可以使用持续效果系统实现各种增益/减益
3. **召唤物控制**: 可以使用状态绑定系统管理召唤物
4. **位置相关效果**: 可以结合持续效果和位置系统实现地形效果
5. **组合技**: 多个角色的状态绑定可以实现组合技能

---

最后更新: 2026-01-29
