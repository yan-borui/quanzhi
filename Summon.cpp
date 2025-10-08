#include <iostream>
#include <string>
#include <unordered_map>
#include <memory>
#include <vector>

class Summon {
protected:
    std::string name;
    double current_hp;
    double max_hp;
    int control;    // 控制能力
    int stealth;    // 潜行能力
    
    // 印记效果
    std::unordered_map<std::string, double> imprints;
    
    // 技能列表
    // 感觉没有必要 
    /*std::vector<std::string> skills;*/

public:
    // 构造函数
    Summon(const std::string& summon_name, double max_health, int ctrl, int stlth)
        : name(summon_name), max_hp(max_health), current_hp(max_health), 
          control(ctrl), stealth(stlth) {}
    
    // 虚析构函数
    virtual ~Summon() = default;
    
    // 纯虚函数 - 技能相关，子类必须实现
    // 玩家类里忘说了，那个learnSkill感觉用不到
	// 我们只需要 override一个函数就行
	// 这里面也是，上面的技能表用不到 
    virtual void useSkill(const std::string& skill_name) = 0;
    virtual void useSkill(int skill_index) = 0;
    
    // 虚函数 - 可以有默认实现，子类可以重写
    virtual void takeDamage(double damage) {
        current_hp -= damage;
        if (current_hp < 0) current_hp = 0;
        std::cout << name << "受到了 " << damage << " 点伤害，当前生命值: " 
                  << current_hp << "/" << max_hp << std::endl;
        
        // 检查是否被摧毁
        if (current_hp <= 0) {
            std::cout << name << "被摧毁了！" << std::endl;
        }
    }
    
    virtual void heal(double amount) {
        current_hp += amount;
        if (current_hp > max_hp) current_hp = max_hp;
        std::cout << name << "恢复了 " << amount << " 点生命值，当前生命值: " 
                  << current_hp << "/" << max_hp << std::endl;
    }
    
    // 印记管理
    virtual void addImprint(const std::string& imprint, double value) {
        imprints[imprint] = value;
        std::cout << name << "获得了 " << imprint << " 印记，值: " << value << std::endl;
    }
    
    virtual double getImprint(const std::string& imprint) const {
        auto it = imprints.find(imprint);
        return (it != imprints.end()) ? it->second : 0.0;
    }
    
    virtual void removeImprint(const std::string& imprint) {
        imprints.erase(imprint);
        std::cout << name << "移除了 " << imprint << " 印记" << std::endl;
    }
    
    virtual void clearAllImprints() {
        imprints.clear();
        std::cout << name << "的所有印记被清除了" << std::endl;
    }
    
    // 技能管理
    // 没啥用，技能自己实现就好
    virtual void learnSkill(const std::string& skill_name) {
        skills.push_back(skill_name);
        std::cout << name << "学会了技能: " << skill_name << std::endl;
    }
    
    virtual bool hasSkill(const std::string& skill_name) const {
        for (const auto& skill : skills) {
            if (skill == skill_name) return true;
        }
        return false;
    }
    
    virtual const std::vector<std::string>& getSkills() const {
        return skills;
    }
    
    virtual int getSkillCount() const {
        return skills.size();
    }
    
    // 属性获取和设置
    virtual double getCurrentHP() const { return current_hp; }
    virtual double getMaxHP() const { return max_hp; }
    virtual int getControl() const { return control; }
    virtual int getStealth() const { return stealth; }
    virtual const std::string& getName() const { return name; }
    
    virtual void setCurrentHP(double hp) { 
        current_hp = hp; 
        if (current_hp > max_hp) current_hp = max_hp;
        if (current_hp < 0) current_hp = 0;
    }
    //同样伞兵，不知所云 
    /*virtual void setMaxHP(double hp) { 
        max_hp = hp; 
        if (current_hp > max_hp) current_hp = max_hp;
    }*/
    
    virtual void setControl(int ctrl) { control = ctrl; }
    virtual void setStealth(int stlth) { stealth = stlth; }
    
    // 状态检查
    virtual bool isAlive() const { return current_hp > 0; }
    virtual bool isFullHealth() const { return current_hp >= max_hp; }
    virtual bool isDestroyed() const { return current_hp <= 0; }
    
    // 召唤物特殊状态
    virtual bool canAct() const { 
        return isAlive() && getImprint("眩晕") == 0 && getImprint("冻结") == 0;
    }
    
    // 显示召唤物信息
    // python里没有析构，我想起来了，那个是自动管理 
    // C++里别忘了析构 
    virtual void displayStatus() const {
        std::cout << "=== " << name << " 状态 ===" << std::endl;
        std::cout << "生命值: " << current_hp << "/" << max_hp;
        if (isDestroyed()) {
            std::cout << " [已摧毁]";
        }
        std::cout << std::endl;
        std::cout << "控制: " << control << std::endl;
        std::cout << "潜行: " << stealth << std::endl;
        
        if (!skills.empty()) {
            std::cout << "技能: ";
            for (size_t i = 0; i < skills.size(); ++i) {
                std::cout << skills[i];
                if (i < skills.size() - 1) std::cout << ", ";
            }
            std::cout << std::endl;
        }
        
        if (!imprints.empty()) {
            std::cout << "印记: ";
            for (const auto& imp : imprints) {
                std::cout << imp.first << "(" << imp.second << ") ";
            }
            std::cout << std::endl;
        }
        
        std::cout << "可行动: " << (canAct() ? "是" : "否") << std::endl;
    }
    
    // 召唤物特殊行为
    virtual void onSummon() {
        std::cout << name << "被召唤到战场！" << std::endl;
    }
    
    virtual void onDestroy() {
        std::cout << name << "从战场上消失！" << std::endl;
    }
    // 不知道为什么召唤物还有回合，看情况决定删不删 
    virtual void onTurnStart() {
        std::cout << name << "的回合开始" << std::endl;
        
        // 回合开始时可以处理一些印记效果，比如持续伤害等
        // 多此一举，不过别忘了持续伤害应该算一种印记 
        /*if (getImprint("燃烧") > 0) {
            double burnDamage = getImprint("燃烧");
            std::cout << name << "受到燃烧效果，受到 " << burnDamage << " 点伤害" << std::endl;
            takeDamage(burnDamage);
        }*/
    }
    
    virtual void onTurnEnd() {
        std::cout << name << "的回合结束" << std::endl;
    }
};
 
