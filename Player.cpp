#include <iostream>
#include <string>
#include <unordered_map>
#include <memory>

class Player {
protected:
    std::string name;
    double current_hp;
    double max_hp;
    int control;    // 控制能力
    int stealth;    // 潜行能力
    
    // 累积效果和印记
    std::unordered_map<std::string, double> accumulations;
    std::unordered_map<std::string, double> imprints;

public:
    // 构造函数
    // 对于有积累的角色，最好在构造函数这里初始化accumulations
	// 对于有印记的角色，在这里通知服务器初始化其他玩家的imprints
	// 服务器异步实现imprints（指等待角色都构造完）
	// 召唤物类还未实现，但到时候需要服务器检查imprints的键 
    Player(const std::string& player_name, double max_health, int ctrl, int stlth)
        : name(player_name), max_hp(max_health), current_hp(max_health), 
          control(ctrl), stealth(stlth) {}
    
    // 虚析构函数
    virtual ~Player() = default;
    
    // 纯虚函数 - 技能相关，子类必须实现
    // 可以有很多技能 
    virtual void useSkill(const std::string& skill_name) = 0;
    virtual void learnSkill(const std::string& skill_name) = 0;
    
    // 虚函数 - 可以有默认实现，子类可以重写
    // 因为hp等安全起见设为private，所以造成伤害需要外部调用该函数而非直接修改hp 
    // 这些std::cout可以改成传给服务器，服务器分发 
    virtual void takeDamage(double damage) {
        current_hp -= damage;
        if (current_hp < 0) current_hp = 0;
        std::cout << name << "受到了 " << damage << " 点伤害，当前生命值: " 
                  << current_hp << "/" << max_hp << std::endl;
    }
    
    virtual void heal(double amount) {
        current_hp += amount;
        if (current_hp > max_hp) current_hp = max_hp;
        std::cout << name << "恢复了 " << amount << " 点生命值，当前生命值: " 
                  << current_hp << "/" << max_hp << std::endl;
    }
    
    // 累积效果管理
    // 想了想，积累和印记肯定可以做到一起，但是这样更清晰 
    virtual void addAccumulation(const std::string& effect, double value) {
        accumulations[effect] += value;
        std::cout << name << "获得了 " << effect << " 累积效果，值: " 
                  << accumulations[effect] << std::endl;
    }
    
    virtual double getAccumulation(const std::string& effect) const {
        auto it = accumulations.find(effect);
        return (it != accumulations.end()) ? it->second : 0.0;
    }
    
    virtual void clearAccumulation(const std::string& effect) {
        accumulations.erase(effect);
        std::cout << name << "清除了 " << effect << " 累积效果" << std::endl;
    }
    
    // 印记管理
    // 和takeDamage同理 
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
    // 这段代码是伞兵吗，存疑 
    /*virtual void setMaxHP(double hp) { 
        max_hp = hp; 
        if (current_hp > max_hp) current_hp = max_hp;
    }*/
    
    virtual void setControl(int ctrl) { control = ctrl; }
    virtual void setStealth(int stlth) { stealth = stlth; }
    
    // 状态检查
    virtual bool isAlive() const { return current_hp > 0; }
    virtual bool isFullHealth() const { return current_hp >= max_hp; }
    
    // 显示玩家信息
    virtual void displayStatus() const {
        std::cout << "=== " << name << " 状态 ===" << std::endl;
        std::cout << "生命值: " << current_hp << "/" << max_hp << std::endl;
        std::cout << "控制: " << control << std::endl;
        std::cout << "潜行: " << stealth << std::endl;
        
        if (!accumulations.empty()) {
            std::cout << "累积效果: ";
            for (const auto& acc : accumulations) {
                std::cout << acc.first << "(" << acc.second << ") ";
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
    }
};
// ok应该没什么其他问题，你们检查吧 
