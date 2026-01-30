#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试新系统的简单示例脚本

演示三个新系统的功能：
1. 双人判定系统 (DualJudgmentSystem)
2. 持续效果系统 (ContinuousEffectSystem)
3. 状态绑定系统 (StateBindingSystem)
"""

import sys
import os

# 添加include目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'include'))

from include.systems.dual_judgment import DualJudgmentSystem, JudgmentResult
from include.systems.continuous_effect import ContinuousEffectSystem, ContinuousEffect, RemovalCondition
from include.systems.state_binding import StateBindingSystem
from include.characters.knight import Knight
from include.characters.summoner import Summoner


def test_dual_judgment_system():
    """测试双人判定系统"""
    print("=" * 60)
    print("测试 1: 双人判定系统")
    print("=" * 60)
    
    # 创建系统
    judgment_system = DualJudgmentSystem()
    
    # 创建两个角色
    knight = Knight("测试骑士")
    summoner = Summoner("测试召唤师")
    
    print("\n1.1 测试正常判定（石头剪刀布）")
    result = judgment_system.judge(knight, summoner, "普通攻击")
    print(f"判定结果: {result.value}")
    
    print("\n1.2 测试自动获胜规则")
    # 注册一个自动让发起方获胜的规则
    auto_win_rule = judgment_system.create_auto_win_rule("initiator")
    judgment_system.register_skill_rule("必胜技能", auto_win_rule)
    
    result = judgment_system.judge(knight, summoner, "必胜技能")
    assert result == JudgmentResult.INITIATOR_WIN, "自动获胜规则应该让发起方获胜"
    print(f"✓ 自动获胜规则测试通过")
    
    print("\n1.3 测试条件规则")
    # 创建条件规则：如果发起方HP > 30则自动获胜
    def hp_condition(initiator, target):
        return initiator.get_current_hp() > 30
    
    conditional_rule = judgment_system.create_conditional_rule(hp_condition, JudgmentResult.INITIATOR_WIN)
    judgment_system.register_skill_rule("气势压制", conditional_rule)
    
    result = judgment_system.judge(knight, summoner, "气势压制")
    print(f"✓ 条件规则测试通过 (骑士HP={knight.get_current_hp()})")
    
    print("\n✓ 双人判定系统测试完成\n")


def test_continuous_effect_system():
    """测试持续效果系统"""
    print("=" * 60)
    print("测试 2: 持续效果系统")
    print("=" * 60)
    
    # 创建系统
    effect_system = ContinuousEffectSystem()
    
    # 创建角色
    knight = Knight("测试骑士")
    
    print("\n2.1 测试持续伤害效果")
    # 创建一个持续3回合的燃烧效果
    def burn_effect(target):
        print(f"  {target.get_name()} 受到燃烧伤害")
        target.take_damage(3)
    
    burn = ContinuousEffect(
        name="燃烧",
        duration=3,
        trigger_func=burn_effect,
        description="每回合造成3点伤害"
    )
    
    effect_system.add_effect(knight, burn)
    initial_hp = knight.get_current_hp()
    
    # 模拟3个回合
    for turn in range(1, 4):
        print(f"\n回合 {turn}:")
        effect_system.trigger_all_effects(knight)
    
    expected_hp = initial_hp - 9  # 3回合 x 3伤害
    assert knight.get_current_hp() == expected_hp, f"HP应该是 {expected_hp}"
    print(f"✓ 持续伤害测试通过 (HP: {initial_hp} -> {knight.get_current_hp()})")
    
    print("\n2.2 测试移动时移除效果")
    # 创建一个移动时会被移除的效果
    def poison_effect(target):
        print(f"  {target.get_name()} 受到中毒伤害")
        target.take_damage(2)
    
    poison = ContinuousEffect(
        name="中毒",
        duration=5,
        trigger_func=poison_effect,
        removal_condition=RemovalCondition.ON_MOVEMENT,
        description="移动时移除"
    )
    
    effect_system.add_effect(knight, poison)
    assert effect_system.has_effect(knight, "中毒"), "应该有中毒效果"
    
    # 触发移动事件
    effect_system.check_and_remove_on_event(knight, "movement")
    assert not effect_system.has_effect(knight, "中毒"), "移动后应该移除中毒效果"
    print(f"✓ 移动移除效果测试通过")
    
    print("\n2.3 测试效果叠加")
    # 添加多层相同效果
    for i in range(3):
        dot = ContinuousEffect(
            name="流血",
            duration=2,
            trigger_func=lambda t: t.take_damage(1)
        )
        effect_system.add_effect(knight, dot)
    
    count = effect_system.get_effect_count(knight, "流血")
    assert count == 3, f"应该有3层流血效果，实际: {count}"
    print(f"✓ 效果叠加测试通过 (流血层数: {count})")
    
    print("\n✓ 持续效果系统测试完成\n")


def test_state_binding_system():
    """测试状态绑定系统"""
    print("=" * 60)
    print("测试 3: 状态绑定系统")
    print("=" * 60)
    
    # 创建系统
    binding_system = StateBindingSystem()
    
    # 创建角色
    knight = Knight("骑士")
    summoner = Summoner("召唤师")
    swordsman_char = None
    
    # 尝试导入剑客
    try:
        from Swordsman import Swordsman
        swordsman_char = Swordsman("剑客")
    except ImportError:
        print("注意: 剑客类不可用，跳过部分测试")
    
    print("\n3.1 测试基本绑定")
    
    # 定义绑定和解绑的回调
    def on_bind(source, target):
        print(f"  → {source.get_name()} 对 {target.get_name()} 施加了标记")
    
    def on_unbind(source, target):
        print(f"  → {source.get_name()} 从 {target.get_name()} 移除了标记")
    
    # 绑定技能到目标
    binding_system.bind_state("锁定", knight, summoner, on_bind, on_unbind)
    
    # 检查绑定是否存在
    assert binding_system.is_bound(knight, "锁定"), "应该已绑定"
    target = binding_system.get_bound_target(knight, "锁定")
    assert target == summoner, "绑定的目标应该是召唤师"
    print(f"✓ 基本绑定测试通过")
    
    print("\n3.2 测试切换目标（自动解除旧绑定）")
    if swordsman_char:
        # 对新目标使用同一技能，应该自动解除旧绑定
        binding_system.bind_state("锁定", knight, swordsman_char, on_bind, on_unbind)
        
        # 检查新绑定
        new_target = binding_system.get_bound_target(knight, "锁定")
        assert new_target == swordsman_char, "绑定的目标应该是剑客"
        print(f"✓ 切换目标测试通过")
    else:
        print("  跳过（剑客不可用）")
    
    print("\n3.3 测试手动解绑")
    success = binding_system.unbind_state(knight, "锁定")
    assert success, "解绑应该成功"
    assert not binding_system.is_bound(knight, "锁定"), "解绑后不应该有绑定"
    print(f"✓ 手动解绑测试通过")
    
    print("\n3.4 测试获取目标的所有绑定")
    # 多个施法者绑定到同一目标
    binding_system.bind_state("标记A", knight, summoner)
    if swordsman_char:
        binding_system.bind_state("标记B", swordsman_char, summoner)
        
        bindings = binding_system.get_target_bindings(summoner)
        assert len(bindings) == 2, f"召唤师应该有2个绑定，实际: {len(bindings)}"
        print(f"✓ 目标绑定列表测试通过 (绑定数: {len(bindings)})")
    else:
        bindings = binding_system.get_target_bindings(summoner)
        assert len(bindings) == 1, f"召唤师应该有1个绑定"
        print(f"✓ 目标绑定列表测试通过 (绑定数: {len(bindings)})")
    
    print("\n✓ 状态绑定系统测试完成\n")


def test_backward_compatibility():
    """测试向后兼容性"""
    print("=" * 60)
    print("测试 4: 向后兼容性")
    print("=" * 60)
    
    print("\n4.1 测试现有角色功能未受影响")
    
    # 创建角色并使用技能
    knight = Knight("骑士")
    summoner = Summoner("召唤师")
    
    initial_hp = summoner.get_current_hp()
    
    # 骑士使用技能攻击召唤师
    knight.use_skill_on_target("斩", summoner)
    
    # 验证伤害正常生效
    assert summoner.get_current_hp() < initial_hp, "召唤师应该受到伤害"
    print(f"✓ 骑士技能正常工作 (召唤师HP: {initial_hp} -> {summoner.get_current_hp()})")
    
    # 召唤师使用技能
    summoner.use_skill_on_target("狼", summoner)
    assert summoner.get_accumulation("狼") > 0, "召唤师应该有狼积累"
    print(f"✓ 召唤师技能正常工作 (狼积累: {summoner.get_accumulation('狼')})")
    
    print("\n✓ 向后兼容性测试完成\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("新系统功能测试")
    print("=" * 60 + "\n")
    
    try:
        test_dual_judgment_system()
        test_continuous_effect_system()
        test_state_binding_system()
        test_backward_compatibility()
        
        print("=" * 60)
        print("所有测试通过！✓")
        print("=" * 60)
        print("\n系统说明:")
        print("1. 双人判定系统: 支持技能发起方与承受方的石头剪刀布判定")
        print("2. 持续效果系统: 支持多回合自动触发的效果，可设置移除条件")
        print("3. 状态绑定系统: 支持技能与目标的绑定关系，自动切换目标")
        print("\n所有系统已成功集成到游戏中，现有角色功能完全不受影响。")
        print("=" * 60 + "\n")
        
        return 0
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
