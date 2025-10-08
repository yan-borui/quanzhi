#pragma once
#include <string>
#include <functional>
#include <iostream>
#include <memory>

/*
 * Skill 类
 * - 表示一个技能的基本信息（名字、冷却）
 * - 提供虚拟的 execute 接口，允许传入回调或在子类中重写以实现具体效果
 * - 提供拷贝/移动语义（默认）
 *
 * 设计注意：
 * - 技能效果不直接修改目标对象（因为这需要引用 Character 类型），
 *   execute 的具体实现可通过传入回调或在更高层调用 Character 的方法来完成。
 *
 * 改进点：
 * - 添加了技能效果回调机制，允许技能执行实际游戏逻辑
 * - 增加了施法者和目标参数，使技能能够影响具体角色
 */

class Character; // 前向声明

class Skill {
private:
    std::string name_;
    int base_cooldown_ = 0;
    int cooldown_ = 0;
    
    // 技能效果回调函数：参数为施法者和可选目标，返回是否施放成功
    std::function<bool(Character& caster, Character* target)> effect_;

public:
    Skill() = default;
    
    // 基础构造函数：只有名称和冷却
    Skill(const std::string& name, int cooldown)
        : name_(name), base_cooldown_(std::max(0, cooldown)), cooldown_(0) {}
    
    // 完整构造函数：包含技能效果回调
    Skill(const std::string& name, int cooldown, 
          std::function<bool(Character& caster, Character* target)> effect)
        : name_(name), base_cooldown_(std::max(0, cooldown)), 
          cooldown_(0), effect_(effect) {}

    virtual ~Skill() = default;

    // 获取技能名
    const std::string& getName() const { return name_; }

    // 获取基础冷却
    int getBaseCooldown() const { return base_cooldown_; }
    
    // 获取当前冷却
    int getCooldown() const { return cooldown_; }

    // 设置基础冷却，边界检查确保冷却 >= 0
    void setBaseCooldown(int cd) { base_cooldown_ = std::max(0, cd); }
    
    // 设置当前冷却
    void setCooldown(int cd) { cooldown_ = std::max(0, cd); }

    // 减少冷却（如果大于0则减1）；返回是否发生了变化
    virtual bool reduceCooldown() {
        if (cooldown_ > 0) {
            --cooldown_;
            return true;
        }
        return false;
    }

    // 检查是否可用（冷却为0）
    virtual bool isAvailable() const { return cooldown_ == 0; }
    
    // 设置技能效果回调
    void setEffect(std::function<bool(Character& caster, Character* target)> effect) {
        effect_ = effect;
    }

    // 执行技能 - 基础版本，需要施法者参数
    // 返回是否成功施放
    virtual bool execute(Character& caster) {
        return execute(caster, nullptr);
    }
    
    // 执行技能 - 完整版本，包含施法者和目标
    // 返回是否成功施放
    virtual bool execute(Character& caster, Character* target) {
        if (!isAvailable()) {
            std::cout << "技能 " << name_ << " 在冷却中 (CD:" << cooldown_ << ")\n";
            return false;
        }
        
        bool success = true;
        
        // 如果有自定义效果回调，执行它
        if (effect_) {
            success = effect_(caster, target);
        } else {
            // 默认效果：只是打印信息
            std::cout << caster.getName() << " 施放了技能: " << name_;
            if (target) {
                std::cout << " 目标: " << target->getName();
            }
            std::cout << std::endl;
        }
        
        // 只有施放成功才进入冷却
        if (success) {
            cooldown_ = base_cooldown_;
        }
        
        return success;
    }
};
