from characters.target import Target
from core.skill import Skill


def test_cd_one_requires_one_complete_intervening_round():
    actor = Target("施法者")
    target = Target("目标")
    skill = Skill("测试技能", cooldown=1, effect=lambda caster, victim: True)

    assert skill.execute_with_target(actor, target)
    assert not skill.is_available()

    skill.reduce_cooldown()  # 下一回合开始
    assert not skill.is_available()

    skill.reduce_cooldown()  # 间隔一回合后的回合开始
    assert skill.is_available()


def test_cd_zero_is_available_on_the_next_round():
    actor = Target("施法者")
    target = Target("目标")
    skill = Skill("测试技能", cooldown=0, effect=lambda caster, victim: True)

    assert skill.execute_with_target(actor, target)
    assert not skill.is_available()

    skill.reduce_cooldown()
    assert skill.is_available()


def test_start_cooldown_uses_declared_base_value():
    skill = Skill("测试技能", cooldown=2)

    skill.start_cooldown()

    assert skill.get_base_cooldown() == 2
    assert skill.get_cooldown() == 2
    assert not skill.is_available()
