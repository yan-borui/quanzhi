# Quanzhi (权智) - 回合制对战游戏

一个基于Python的回合制对战游戏，支持多角色选择和动态对战。

## 特性

- 🎮 **灵活的角色系统**: 支持2-6名玩家对战
- 🏭 **可扩展架构**: 使用工厂模式轻松添加新角色
- 🎯 **多样化战斗**: 石头剪刀布决定先手，技能系统丰富
- 🛡️ **复杂机制**: 支持控制效果、印记、累积效果、邻接系统等

## 快速开始

### 运行游戏

```bash
cd include
python3 main.py
```

### 游戏模式

1. **自定义角色选择**: 从所有可用角色中选择2-6个进行对战
2. **默认模式**: 快速开始，使用预设的骑士、召唤师、剑客三方混战

### 现有角色

- **骑士**: 防御型战士，拥有强大的盾技能可以回退状态
- **召唤师**: 召唤系输出，积累召唤物发动强力齐攻
- **剑客**: 近战输出，通过剑意印记实现连击

## 添加新角色

详见 [CHARACTER_GUIDE.md](CHARACTER_GUIDE.md) 了解如何扩展游戏添加新角色。

示例新角色已包含在 `include/Mage.py` 中。

## 项目结构

```
quanzhi/
├── include/
│   ├── Character.py           # 角色基类
│   ├── Skill.py               # 技能系统
│   ├── CharacterFactory.py    # 角色工厂和注册表
│   ├── character_init.py      # 角色注册
│   ├── character_selection.py # 角色选择UI
│   ├── Knight.py              # 骑士角色
│   ├── Summoner.py            # 召唤师角色
│   ├── Swordsman.py           # 剑客角色
│   ├── Mage.py                # 法师角色（示例）
│   ├── main.py                # 游戏主程序
│   └── ...
├── CHARACTER_GUIDE.md         # 角色开发指南
└── README.md                  # 本文件
```

## 系统架构

### CharacterFactory 模式

游戏使用工厂模式管理角色创建：

```python
from CharacterFactory import get_character_factory

factory = get_character_factory()
knight = factory.create("knight", "我的骑士")
summoner = factory.create("summoner")
```

### 动态玩家数量

Game类现在接受角色列表，支持任意数量的玩家：

```python
from main import Game

characters = [
    factory.create("knight", "K1"),
    factory.create("knight", "K2"),
    factory.create("summoner", "S1"),
    # ... 最多6个角色
]

game = Game(characters)
game.start()
```

## 开发

### 运行测试

```bash
cd include
python3 -m py_compile *.py  # 语法检查
```

### 代码规范

- 使用中文注释和文档字符串
- 遵循PEP 8编码规范
- 新角色必须继承Character基类
- 使用类型注解提高代码可读性

## 许可证

见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Pull Request 添加新角色或改进游戏机制！
