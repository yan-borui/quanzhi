#pragma once
#include <string>
#include <unordered_map>
#include <memory>
#include <iostream>
#include <algorithm>
#include <optional>
#include <functional>
#include "Skill.h"

/*
 * Character 抽象基类
 * - 提取 Player 和 Summon 的公共属性与方法
 * - 管理：生命值、控制、潜行、技能、印记（imprints）和累积效果（accumulations）
 * - 提供边界检查：map 访问、hp 范围、印记/累积减值不越界、技能检查等
 *
 * 设计说明：
 * - 只包含与角色状态与技能管理相关的通用逻辑，具体的 useSkill() 为纯虚。
 * - 技能容器以 unordered_map<name, Skill> 保存（值语义），避免频繁 new/delete。
 *
 * 改进点：
 * - 使用 std::optional 和 std::reference_wrapper 提供更安全的技能访问
 * - 增加了常量正确性
 * - 改进了摧毁状态的检测逻辑
 */

class Character {
public:
    Character() = default;

    Character(const std::string& name, int max_hp, int control = 0, int stealth = 0)
        : name_(name),
          max_hp_(std::max(0, max_hp)),
          current_hp_(std::max(0, max_hp_)),
          control_(control),
          stealth_(stealth) {}

    virtual ~Character() = default;
    
    // 禁用拷贝，启用移动
    Character(const Character&) = delete;
    Character& operator=(const Character&) = delete;
    Character(Character&&) = default;
    Character& operator=(Character&&) = default;
    
    // 子类必须实现技能使用
    virtual void useSkill(const std::string& skill_name) = 0;
    
    // 带目标的技能使用（可选实现）
    virtual void useSkill(const std::string& skill_name, Character& target) {
        // 默认实现忽略目标，子类可以重写
        useSkill(skill_name);
    }

    // 受伤并显示（确保边界）
    virtual void takeDamage(int damage) {
        if (damage <= 0) {
            std::cout << name_ << " 未受到有效伤害: " << damage << std::endl;
            return;
        }
        
        bool wasAlive = isAlive(); // 记录受伤前状态
        
        current_hp_ -= damage;
        if (current_hp_ < 0) current_hp_ = 0;
        std::cout << name_ << " 受到了 " << damage << " 点伤害，当前生命值: "
                  << current_hp_ << "/" << max_hp_ << std::endl;
        
        // 如果从存活状态变为摧毁状态，触发摧毁回调
        if (wasAlive && isDestroyed()) {
            onDestroy();
        }
    }

    // 治疗并显示
    virtual void heal(int amount) {
        if (amount <= 0) {
            std::cout << name_ << " 没有被有效治疗: " << amount << std::endl;
            return;
        }
        current_hp_ += amount;
        if (current_hp_ > max_hp_) current_hp_ = max_hp_;
        std::cout << name_ << " 恢复了 " << amount << " 点生命值，当前生命值: "
                  << current_hp_ << "/" << max_hp_ << std::endl;
    }

    // 技能管理
    bool hasSkill(const std::string& skill_name) const {
        return skills_.find(skill_name) != skills_.end();
    }

    // 获取技能冷却（-1 表示不存在）
    int getSkillCooldown(const std::string& skill_name) const {
        auto it = skills_.find(skill_name);
        return (it != skills_.end()) ? it->second.getCooldown() : -1;
    }

    // 设置技能冷却（如果技能存在）
    void setSkillCooldown(const std::string& skill_name, int cooldown) {
        auto it = skills_.find(skill_name);
        if (it != skills_.end()) {
            it->second.setCooldown(cooldown);
        }
    }

    // 将所有技能冷却-1（不小于0）
    void reduceAllCooldowns() {
        for (auto& kv : skills_) {
            kv.second.reduceCooldown();
        }
    }

    // 添加或替换技能
    void addOrReplaceSkill(const Skill& skill) {
        if (skill.getName().empty()) return;
        skills_[skill.getName()] = skill;
    }
    
    // 添加或替换技能（移动语义版本）
    void addOrReplaceSkill(Skill&& skill) {
        if (skill.getName().empty()) return;
        skills_[skill.getName()] = std::move(skill);
    }

    // 获取技能引用（更安全的访问方式）
    std::optional<std::reference_wrapper<Skill>> getSkill(const std::string& skill_name) {
        auto it = skills_.find(skill_name);
        if (it == skills_.end()) return std::nullopt;
        return std::ref(it->second);
    }
    
    // 获取常量技能引用
    std::optional<std::reference_wrapper<const Skill>> getSkill(const std::string& skill_name) const {
        auto it = skills_.find(skill_name);
        if (it == skills_.end()) return std::nullopt;
        return std::cref(it->second);
    }

    // 印记管理（get/set/remove/clear）
    void addImprint(const std::string& imprint, int value) {
        if (imprint.empty()) return;
        imprints_[imprint] = value;
        std::cout << name_ << " 获得了 " << imprint << " 印记，值: " << value << std::endl;
    }

    int getImprint(const std::string& imprint) const {
        auto it = imprints_.find(imprint);
        return (it != imprints_.end()) ? it->second : 0;
    }

    // 安全地减少一层印记（不会变为负数）
    void removeImprint(const std::string& imprint) {
        auto it = imprints_.find(imprint);
        if (it == imprints_.end()) {
            std::cout << name_ << " 不存在印记: " << imprint << std::endl;
            return;
        }
        if (it->second > 1) {
            --(it->second);
            std::cout << name_ << " 移除了一层 " << imprint << " 印记，剩余: " << it->second << std::endl;
        } else {
            imprints_.erase(it);
            std::cout << name_ << " 清除了 " << imprint << " 印记" << std::endl;
        }
    }

    void clearImprint(const std::string& imprint) {
        auto it = imprints_.find(imprint);
        if (it != imprints_.end()) {
            imprints_.erase(it);
            std::cout << name_ << " 清除了 " << imprint << " 累积效果" << std::endl;
        }
    }

    // 累积效果管理（与 Player 的 accumulations 功能一致）
    void addAccumulation(const std::string& effect, int value) {
        if (effect.empty()) return;
        accumulations_[effect] += value;
        std::cout << name_ << " 获得了 " << effect << " 累积效果，值: " << accumulations_[effect] << std::endl;
    }

    int getAccumulation(const std::string& effect) const {
        auto it = accumulations_.find(effect);
        return (it != accumulations_.end()) ? it->second : 0;
    }

    void reduceAccumulation(const std::string& effect, int number) {
        auto it = accumulations_.find(effect);
        if (it == accumulations_.end()) {
            std::cout << name_ << " 没有累积效果: " << effect << std::endl;
            return;
        }
        it->second -= number;
        if (it->second <= 0) {
            accumulations_.erase(it);
            std::cout << name_ << " 消耗并清除了 " << effect << " 累积效果" << std::endl;
        } else {
            std::cout << name_ << " 消耗了 " << effect << " 累积效果，剩余: " << it->second << std::endl;
        }
    }

    void clearAccumulation(const std::string& effect) {
        auto it = accumulations_.find(effect);
        if (it != accumulations_.end()) {
            accumulations_.erase(it);
            std::cout << name_ << " 清除了 " << effect << " 累积效果" << std::endl;
        }
    }

    // 属性访问与设置（带边界检查）
    int getCurrentHP() const { return current_hp_; }
    int getMaxHP() const { return max_hp_; }
    int getControl() const { return control_; }
    int getStealth() const { return stealth_; }
    const std::string& getName() const { return name_; }

    void setCurrentHP(int hp) {
        current_hp_ = std::clamp(hp, 0, max_hp_);
    }

    void setMaxHP(int max_hp) {
        max_hp_ = std::max(0, max_hp);
        if (current_hp_ > max_hp_) current_hp_ = max_hp_;
    }

    void setControl(int ctrl) { control_ = ctrl; }
    void setStealth(int stlth) { stealth_ = stlth; }

    // 状态检查
    bool isAlive() const { return current_hp_ > 0; }
    bool isFullHealth() const { return current_hp_ >= max_hp_; }
    bool isDestroyed() const { return current_hp_ <= 0; }

    bool canAct() const { return isAlive() && control_ == 0; }

    // 输出状态
    virtual void displayStatus() const {
        std::cout << "=== " << name_ << " 状态 ===" << std::endl;
        std::cout << "生命值: " << current_hp_ << "/" << max_hp_;
        if (isDestroyed()) std::cout << " [已摧毁]";
        std::cout << std::endl;
        std::cout << "控制: " << control_ << std::endl;
        std::cout << "潜行: " << stealth_ << std::endl;

        if (!skills_.empty()) {
            std::cout << "技能列表: ";
            for (const auto& kv : skills_) {
                std::cout << kv.first << "(CD:" << kv.second.getCooldown() << ") ";
            }
            std::cout << std::endl;
        }

        if (!accumulations_.empty()) {
            std::cout << "累积效果: ";
            for (const auto& kv : accumulations_) {
                std::cout << kv.first << "(" << kv.second << ") ";
            }
            std::cout << std::endl;
        }

        if (!imprints_.empty()) {
            std::cout << "印记: ";
            for (const auto& kv : imprints_) {
                std::cout << kv.first << "(" << kv.second << ") ";
            }
            std::cout << std::endl;
        }

        std::cout << "可行动: " << (canAct() ? "是" : "否") << std::endl;
    }

    // 特殊事件钩子，子类可重写
    virtual void onSummon() { std::cout << name_ << " 被召唤到战场！" << std::endl; }
    virtual void onDestroy() { std::cout << name_ << " 从战场上消失！" << std::endl; }

protected:
    std::string name_;
    int current_hp_ = 0;
    int max_hp_ = 0;
    int control_ = 0;
    int stealth_ = 0;

    std::unordered_map<std::string, Skill> skills_;
    std::unordered_map<std::string, int> imprints_;
    std::unordered_map<std::string, int> accumulations_;
};
