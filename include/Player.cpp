#pragma once
#include "Character.h"

/*
 * Player 派生类
 * - 继承 Character，提供玩家特有的构造与 useSkill 实现（示例）
 * - 保持与原来 Player 类相似的接口与行为
 *
 * 改进点：
 * - 支持带目标的技能施放
 * - 使用更安全的技能访问方式
 */

class Player : public Character {
public:
    Player() = default;

    Player(const std::string& player_name, int max_health, int ctrl = 0, int stlth = 0)
        : Character(player_name, max_health, ctrl, stlth) {
        // 如果玩家需要初始化 accumulations 或通知服务器 imprints，
        // 在高层逻辑中处理（这里仅做本地初始化）
    }

    virtual ~Player() = default;

    // 示例性的 useSkill：检查技能存在且可用，然后调用 Skill::execute
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
            std::cout << "技能 " << skill_name << " 正在冷却 (CD:" << skill.getCooldown() << ")" << std::endl;
            return;
        }

        // 执行技能（包含目标信息）
        bool ok = skill.execute(*this, &target);
        if (ok) {
            std::cout << name_ << " 对 " << target.getName() << " 施放了技能 " << skill_name << std::endl;
        }
    }
};
