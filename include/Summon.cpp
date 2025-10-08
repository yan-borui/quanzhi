#pragma once
#include "Character.h"

/*
 * Summon 派生类
 * - 表示召唤物，行为类似于原先的 Summon 类
 * - 可以重写 onSummon/onDestroy/takeDamage 等行为
 *
 * 改进点：
 * - 改进了摧毁检测逻辑，确保只在状态变化时触发 onDestroy
 * - 支持带目标的技能施放
 */

class Summon : public Character {
public:
    Summon() = default;

    Summon(const std::string& summon_name, int max_health, int ctrl = 0, int stlth = 0)
        : Character(summon_name, max_health, ctrl, stlth) {}

    virtual ~Summon() = default;

    // 子类必须实现的技能释放（此处提供默认示例）
    virtual void useSkill(const std::string& skill_name) override {
        useSkill(skill_name, *this); // 默认目标为自己
    }
    
    // 带目标的技能使用
    virtual void useSkill(const std::string& skill_name, Character& target) override {
        if (skill_name.empty()) {
            std::cout << "技能名为空，无法施放" << std::endl;
            return;
        }
        
        // 使用更安全的技能访问方式
        auto skill_opt = getSkill(skill_name);
        if (!skill_opt) {
            std::cout << name_ << " 没有技能: " << skill_name << std::endl;
            return;
        }
        
        Skill& skill = skill_opt->get();
        if (!skill.isAvailable()) {
            std::cout << "技能 " << skill_name << " 在冷却中 (CD:" << skill.getCooldown() << ")\n";
            return;
        }

        // 执行技能（包含目标信息）
        bool ok = skill.execute(*this, &target);
        if (ok) {
            std::cout << name_ << " 对 " << target.getName() << " 施放了技能 " << skill_name << std::endl;
        }
    }

    // 重写 takeDamage 实现更安全的摧毁回调
    virtual void takeDamage(int damage) override {
        bool wasAlive = isAlive(); // 记录受伤前状态
        
        Character::takeDamage(damage);
        
        // 基类已处理摧毁回调，这里可以添加召唤物特有的逻辑
        if (wasAlive && isDestroyed()) {
            std::cout << "召唤物 " << name_ << " 被摧毁！" << std::endl;
        }
    }

    virtual void onSummon() override {
        std::cout << name_ << " 被召唤到战场（Summon::onSummon）！" << std::endl;
    }

    virtual void onDestroy() override {
        std::cout << name_ << " 从战场上消失（Summon::onDestroy）！" << std::endl;
    }
};
