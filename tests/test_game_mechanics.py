# -*- coding: utf-8 -*-
"""
test_game_mechanics.py - 游戏机制更新测试
测试治疗师、召唤师、游侠、卖油翁的技能与交互机制
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "include"))

from characters.healer import Healer
from characters.summoner import Summoner
from characters.ranger import Ranger
from characters.oil_master import OilMaster
from core.player import Player
from main import Game


# ========== 治疗师 (Healer) 测试 ==========

class TestHealerDamageReduction:
    """治疗师自我治疗减伤状态测试"""

    def test_big_heal_self_grants_damage_reduction(self):
        """大血包治疗自己时，附加减伤状态（+2回合）"""
        healer = Healer()
        healer.set_current_hp(10)
        healer.use_skill_on_target("大血包", healer)
        assert healer.damage_reduction_turns == 2

    def test_small_heal_self_grants_damage_reduction(self):
        """小血包治疗自己时，附加减伤状态（+1回合）"""
        healer = Healer()
        healer.set_current_hp(10)
        healer.use_skill_on_target("小血包", healer)
        assert healer.damage_reduction_turns == 1

    def test_heal_other_no_damage_reduction(self):
        """治疗他人时不附加减伤状态"""
        healer = Healer()
        target = Player("目标", 60)
        target.set_current_hp(30)
        healer.use_skill_on_target("大血包", target)
        assert healer.damage_reduction_turns == 0

    def test_damage_reduction_cap_at_2(self):
        """减伤状态回合上限为2"""
        healer = Healer()
        healer.set_current_hp(10)
        healer.use_skill_on_target("大血包", healer)  # +2
        assert healer.damage_reduction_turns == 2
        # Reset cooldown for testing
        healer.get_skill("小血包").set_cooldown(0)
        healer.set_current_hp(10)
        healer.use_skill_on_target("小血包", healer)  # +1 but capped at 2
        assert healer.damage_reduction_turns == 2

    def test_damage_reduction_stacks_turns(self):
        """减伤状态叠加回合数"""
        healer = Healer()
        healer.set_current_hp(10)
        healer.use_skill_on_target("小血包", healer)  # +1
        assert healer.damage_reduction_turns == 1
        healer.get_skill("小血包").set_cooldown(0)
        healer.set_current_hp(10)
        healer.use_skill_on_target("小血包", healer)  # +1 -> 2
        assert healer.damage_reduction_turns == 2

    def test_damage_reduction_halves_damage(self):
        """减伤状态下受到的伤害降低50%"""
        healer = Healer()
        healer.damage_reduction_turns = 2
        healer.set_current_hp(30)
        healer.take_damage(10)
        # 10 // 2 = 5, so HP should be 30 - 5 = 25
        assert healer.get_current_hp() == 25

    def test_damage_reduction_decrement_on_turn_start(self):
        """回合开始时递减减伤回合数"""
        healer = Healer()
        healer.damage_reduction_turns = 2
        healer.on_turn_start()
        assert healer.damage_reduction_turns == 1
        healer.on_turn_start()
        assert healer.damage_reduction_turns == 0

    def test_damage_reduction_minimum_damage_is_1(self):
        """减伤后最小伤害为1"""
        healer = Healer()
        healer.damage_reduction_turns = 2
        healer.set_current_hp(30)
        healer.take_damage(1)
        # 1 // 2 = 0, but min is 1
        assert healer.get_current_hp() == 29


class TestHealerShield:
    """治疗师立盾机制测试"""

    def test_shield_creates_entity(self):
        """套盾生成立盾实体，血量为3"""
        healer = Healer()
        healer.use_skill_on_target("套盾", healer)
        assert healer.shield_hp == 3

    def test_shield_stacking_adds_hp(self):
        """立盾已存在时再次使用，增加3血量"""
        healer = Healer()
        healer.shield_hp = 3
        healer.get_skill("套盾").set_cooldown(0)
        healer.use_skill_on_target("套盾", healer)
        assert healer.shield_hp == 6

    def test_shield_absorbs_damage(self):
        """伤害优先扣除立盾血量"""
        healer = Healer()
        healer.shield_hp = 3
        healer.set_current_hp(30)
        healer.take_damage(2)
        assert healer.shield_hp == 1
        assert healer.get_current_hp() == 30  # 本体不受伤

    def test_shield_overflow_discarded(self):
        """溢出伤害不传递给本体"""
        healer = Healer()
        healer.shield_hp = 3
        healer.set_current_hp(30)
        healer.take_damage(6)  # 3 shield, 3 overflow discarded
        assert healer.shield_hp == 0
        assert healer.get_current_hp() == 30  # 本体不受伤

    def test_shield_break_clears_controls_during_shield(self):
        """盾碎时自动清除拥有立盾期间受到的控制"""
        healer = Healer()
        healer.shield_hp = 3
        healer.add_control("纱袋", 1)  # 拥有盾期间受到的控制
        healer.take_damage(5)  # 盾碎
        assert healer.shield_hp == 0
        assert not healer.has_control("纱袋")

    def test_shield_break_does_not_clear_pre_shield_controls(self):
        """盾碎不清除拥有立盾前受到的控制"""
        healer = Healer()
        healer.add_control("纱袋", 1)  # 拥有盾之前的控制
        healer.shield_hp = 3
        healer._shield_controls.clear()  # 重新设置盾，不记录之前的控制
        healer.take_damage(5)  # 盾碎
        assert healer.has_control("纱袋")  # 之前的控制仍在

    def test_imprints_pass_through_shield(self):
        """印记直接施加在本体，立盾不承担"""
        healer = Healer()
        healer.shield_hp = 3
        healer.add_imprint("标记", 1)
        assert healer.get_imprint("标记") == 1

    def test_controls_still_apply_with_shield(self):
        """立盾存在时角色依然受控制效果影响"""
        healer = Healer()
        healer.shield_hp = 3
        healer.add_control("纱袋", 1)
        assert healer.is_controlled()


# ========== 召唤师 (Summoner) 测试 ==========

class TestSummonerWolf:
    """召唤师狼技能重构测试"""

    def test_wolf_self_accumulates(self):
        """目标为自己时积累+1"""
        summoner = Summoner()
        summoner.use_skill_on_target("狼", summoner)
        assert summoner.get_accumulation("狼") == 1

    def test_wolf_other_applies_vulnerability(self):
        """目标为他人时施加易伤状态"""
        summoner = Summoner()
        target = Player("目标", 60)
        summoner.use_skill_on_target("狼", target)
        assert target.get_accumulation("易伤") == 20

    def test_wolf_other_no_attack_buff(self):
        """目标为他人时不施加攻击强化（攻击强化由熊提供）"""
        summoner = Summoner()
        target = Player("目标", 60)
        summoner.use_skill_on_target("狼", target)
        assert target.get_accumulation("攻击强化") == 0

    def test_wolf_vulnerability_stacks_linearly(self):
        """易伤倍率可线性叠加"""
        summoner = Summoner()
        target = Player("目标", 60)
        summoner.use_skill_on_target("狼", target)
        summoner.get_skill("狼").set_cooldown(0)
        summoner.use_skill_on_target("狼", target)
        summoner.get_skill("狼").set_cooldown(0)
        summoner.use_skill_on_target("狼", target)
        assert target.get_accumulation("易伤") == 60

    def test_wolf_no_attack_buff_stacks(self):
        """狼不施加攻击强化"""
        summoner = Summoner()
        target = Player("目标", 60)
        summoner.use_skill_on_target("狼", target)
        summoner.get_skill("狼").set_cooldown(0)
        summoner.use_skill_on_target("狼", target)
        assert target.get_accumulation("攻击强化") == 0

    def test_wolf_self_no_vulnerability(self):
        """目标为自己时不施加易伤"""
        summoner = Summoner()
        summoner.use_skill_on_target("狼", summoner)
        assert summoner.get_accumulation("易伤") == 0

    def test_wolf_self_no_attack_buff(self):
        """目标为自己时不施加攻击强化"""
        summoner = Summoner()
        summoner.use_skill_on_target("狼", summoner)
        assert summoner.get_accumulation("攻击强化") == 0


class TestVulnerabilityMechanic:
    """易伤效果机制测试"""

    def test_vulnerability_increases_damage(self):
        """有易伤的目标受到攻击时伤害增加"""
        target = Player("目标", 60)
        target.add_accumulation("易伤", 20)  # 20%易伤
        target.take_damage(10)
        # 10 + 10*20//100 = 10 + 2 = 12
        assert target.get_current_hp() == 48

    def test_vulnerability_consumed_after_hit(self):
        """易伤在受到攻击后被消耗"""
        target = Player("目标", 60)
        target.add_accumulation("易伤", 20)
        target.take_damage(10)
        assert target.get_accumulation("易伤") == 0

    def test_vulnerability_stacked_increases_more(self):
        """叠加的易伤提供更高伤害增加"""
        target = Player("目标", 60)
        target.add_accumulation("易伤", 60)  # 60%易伤
        target.take_damage(10)
        # 10 + 10*60//100 = 10 + 6 = 16
        assert target.get_current_hp() == 44

    def test_no_vulnerability_normal_damage(self):
        """没有易伤的目标受到正常伤害"""
        target = Player("目标", 60)
        target.take_damage(10)
        assert target.get_current_hp() == 50


class TestAttackBuffMechanic:
    """攻击强化效果机制测试"""

    def test_attack_buff_increases_damage(self):
        """攻击强化增加造成的伤害"""
        from characters.target import Target
        attacker = Target("攻击者")
        attacker.add_accumulation("攻击强化", 6)
        target = Player("目标", 60)
        attacker.use_skill_on_target("平A", target)
        # 基础伤害6 + 攻击强化6 = 12
        assert target.get_current_hp() == 48

    def test_attack_buff_consumed_after_attack(self):
        """攻击强化在攻击后被消耗"""
        from characters.target import Target
        attacker = Target("攻击者")
        attacker.add_accumulation("攻击强化", 6)
        target = Player("目标", 60)
        attacker.use_skill_on_target("平A", target)
        assert attacker.get_accumulation("攻击强化") == 0

    def test_attack_buff_stacked_increases_more(self):
        """叠加的攻击强化提供更高伤害增加"""
        from characters.target import Target
        attacker = Target("攻击者")
        attacker.add_accumulation("攻击强化", 12)
        target = Player("目标", 60)
        attacker.use_skill_on_target("平A", target)
        # 基础伤害6 + 攻击强化12 = 18
        assert target.get_current_hp() == 42

    def test_no_attack_buff_normal_damage(self):
        """没有攻击强化时造成正常伤害"""
        from characters.target import Target
        attacker = Target("攻击者")
        target = Player("目标", 60)
        attacker.use_skill_on_target("平A", target)
        assert target.get_current_hp() == 54


# ========== 游侠 (Ranger) 测试 ==========

class TestRangerSandbag:
    """游侠纱袋技能位移测试"""

    def test_sandbag_displacement(self):
        """纱袋强制将目标移动到游侠所在地块"""
        ranger = Ranger()
        target = Player("目标", 60)
        ranger.set_block_id(100)
        target.set_block_id(200)
        ranger.use_skill_on_target("纱袋", target)
        assert target.get_block_id() == 100

    def test_sandbag_control_still_applied(self):
        """纱袋仍然施加控制效果"""
        ranger = Ranger()
        target = Player("目标", 60)
        ranger.use_skill_on_target("纱袋", target)
        assert target.has_control("纱袋")

    def test_sandbag_no_stack(self):
        """纱袋不可叠加"""
        ranger = Ranger()
        target = Player("目标", 60)
        ranger.use_skill_on_target("纱袋", target)
        ranger.get_skill("纱袋").set_cooldown(0)
        ranger.use_skill_on_target("纱袋", target)
        assert target.get_control("纱袋") == 1


# ========== 卖油翁 (Oil Master) 测试 ==========

class TestOilMasterPot:
    """卖油翁一锅油技能与喝油交互测试"""

    def test_pot_self_target(self):
        """一锅油瞬发，自身油锅计数+1"""
        oil_master = OilMaster()
        oil_master.use_skill("一锅油")
        assert oil_master.oil_pot_count == 1

    def test_pot_increments_count(self):
        """多次使用一锅油叠加计数"""
        oil_master = OilMaster()
        oil_master.use_skill("一锅油")
        oil_master.get_skill("一锅油").set_cooldown(0)
        oil_master.use_skill("一锅油")
        assert oil_master.oil_pot_count == 2

    def test_drink_oil_heals(self):
        """喝油HP+3"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 1
        drinker = Player("喝油者", 60)
        drinker.set_current_hp(50)
        result = oil_master.drink_oil(drinker)
        assert result is True
        assert drinker.get_current_hp() == 53

    def test_drink_oil_consumes_count(self):
        """喝油消耗1个油锅计数"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 2
        drinker = Player("喝油者", 60)
        oil_master.drink_oil(drinker)
        assert oil_master.oil_pot_count == 1

    def test_drink_oil_no_pots(self):
        """没有油锅时无法喝油"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 0
        drinker = Player("喝油者", 60)
        result = oil_master.drink_oil(drinker)
        assert result is False

    def test_drink_oil_any_character(self):
        """任何角色都可以喝油"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 3
        healer = Healer()
        healer.set_current_hp(20)
        ranger = Ranger()
        ranger.set_current_hp(50)

        oil_master.drink_oil(healer)
        assert healer.get_current_hp() == 23
        assert oil_master.oil_pot_count == 2

        oil_master.drink_oil(ranger)
        assert ranger.get_current_hp() == 53
        assert oil_master.oil_pot_count == 1

    def test_pot_ignores_target_param(self):
        """一锅油忽略目标参数，总是对自己生效"""
        oil_master = OilMaster()
        target = Player("目标", 60)
        oil_master.use_skill_on_target("一锅油", target)
        assert oil_master.oil_pot_count == 1


class TestOilMasterTurnReset:
    """卖油翁回合状态重置测试"""

    def test_oil_pots_reset_on_turn_start(self):
        """回合开始时重置oil_pots为1"""
        oil_master = OilMaster()
        oil_master.oil_pots = 0
        oil_master.on_turn_start()
        assert oil_master.oil_pots == 1

    def test_face_skill_reusable_after_turn_start(self):
        """倒你脸上在新回合开始后可以再次使用"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 3
        target = Player("目标", 60)
        # 使用一次倒你脸上（消耗1个oil_pot_count和1个oil_pots）
        oil_master.use_skill_on_target("倒你脸上", target)
        assert oil_master.oil_pots == 0
        assert oil_master.oil_pot_count == 2
        # 本回合不能再使用（oil_pots限制）
        old_hp = target.get_current_hp()
        oil_master.use_skill_on_target("倒你脸上", target)
        assert target.get_current_hp() == old_hp  # HP不变，技能未生效
        # 新回合开始后重置oil_pots
        oil_master.on_turn_start()
        assert oil_master.oil_pots == 1


class TestOilMasterFaceRequiresOil:
    """卖油翁倒你脸上需要并消耗油锅测试"""

    def test_face_consumes_oil_pot_count(self):
        """倒你脸上消耗油锅计数"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 2
        target = Player("目标", 60)
        oil_master.use_skill_on_target("倒你脸上", target)
        assert oil_master.oil_pot_count == 1

    def test_face_fails_without_oil_pot_count(self):
        """没有油锅时无法使用倒你脸上"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 0
        target = Player("目标", 60)
        old_hp = target.get_current_hp()
        oil_master.use_skill_on_target("倒你脸上", target)
        assert target.get_current_hp() == old_hp  # 目标HP不变

    def test_face_cannot_use_unlimited(self):
        """一锅油被使用后不能无限次倒你脸上"""
        oil_master = OilMaster()
        oil_master.use_skill("一锅油")
        assert oil_master.oil_pot_count == 1
        target = Player("目标", 60)
        # 使用一次倒你脸上
        oil_master.use_skill_on_target("倒你脸上", target)
        assert oil_master.oil_pot_count == 0
        # 新回合重置oil_pots
        oil_master.on_turn_start()
        # 再次使用应失败（没有油锅了）
        old_hp = target.get_current_hp()
        oil_master.use_skill_on_target("倒你脸上", target)
        assert target.get_current_hp() == old_hp

    def test_drink_oil_also_consumes(self):
        """喝油也消耗油锅计数，喝完后不能再倒"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 1
        drinker = Player("喝油者", 60)
        oil_master.drink_oil(drinker)
        assert oil_master.oil_pot_count == 0
        # 没有油锅了，倒你脸上应失败
        target = Player("目标", 60)
        old_hp = target.get_current_hp()
        oil_master.use_skill_on_target("倒你脸上", target)
        assert target.get_current_hp() == old_hp


class TestSummonerTargetSelection:
    """召唤师技能目标选择测试"""

    def test_wolf_on_other_target(self):
        """狼技能可指定他人为目标，施加易伤但不施加攻击强化"""
        summoner = Summoner()
        target = Player("目标", 60)
        summoner.use_skill_on_target("狼", target)
        assert target.get_accumulation("易伤") == 20
        assert target.get_accumulation("攻击强化") == 0

    def test_bear_on_self(self):
        """熊技能对自己使用时积累+1"""
        summoner = Summoner()
        summoner.use_skill_on_target("熊", summoner)
        assert summoner.get_accumulation("熊") == 1

    def test_bear_on_other_applies_attack_buff(self):
        """熊技能对他人使用时施加攻击强化"""
        summoner = Summoner()
        target = Player("目标", 60)
        summoner.use_skill_on_target("熊", target)
        assert target.get_accumulation("攻击强化") == 6
        assert summoner.get_accumulation("熊") == 0


class TestDrinkOilGameAction:
    """喝油全局交互机制测试（Game层面）"""

    def test_drink_oil_action_appears_when_oil_available(self):
        """场上存在卖油翁且油锅计数>0时，动作列表包含喝油"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 1
        target = Player("战士", 60)
        game = Game([oil_master, target])
        actions = game.get_available_actions(target)
        assert "[交互] 喝油 (HP+3)" in actions

    def test_drink_oil_action_absent_when_no_oil(self):
        """场上卖油翁油锅计数为0时，不显示喝油"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 0
        target = Player("战士", 60)
        game = Game([oil_master, target])
        actions = game.get_available_actions(target)
        assert "[交互] 喝油 (HP+3)" not in actions

    def test_drink_oil_action_absent_when_no_oil_master(self):
        """场上无卖油翁时，不显示喝油"""
        p1 = Player("战士1", 60)
        p2 = Player("战士2", 60)
        game = Game([p1, p2])
        actions = game.get_available_actions(p1)
        assert "[交互] 喝油 (HP+3)" not in actions

    def test_execute_drink_oil_action(self):
        """执行喝油动作：HP+3，油锅计数-1"""
        oil_master = OilMaster()
        oil_master.oil_pot_count = 2
        target = Player("战士", 60)
        target.set_current_hp(50)
        game = Game([oil_master, target])
        result = game.execute_player_action(target, "[交互] 喝油 (HP+3)")
        assert result is True
        assert target.get_current_hp() == 53
        assert oil_master.oil_pot_count == 1

    def test_pot_skill_skips_target_selection(self):
        """一锅油在execute_player_action中跳过目标选择"""
        oil_master = OilMaster()
        game = Game([oil_master, Player("敌人", 60)])
        result = game.execute_player_action(oil_master, "技能:一锅油")
        assert result is True
        assert oil_master.oil_pot_count == 1
