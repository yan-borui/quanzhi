# Quanzhi (权智) - 回合制对战游戏

一个基于 Python 的回合制多人对战游戏，拥有丰富的角色系统、插件化架构和图形客户端。

## 特性

- **灵活的角色系统**: 支持 2~6 名玩家对战，16 个内置可选角色
- **可扩展插件架构**: 通过插件目录或 `setuptools` entry points 动态加载自定义角色
- **多样化战斗机制**: 石头剪刀布决定先手，技能冷却、印记、控制、召唤物等机制
- **多系统联动**: 双人判定系统、持续效果系统、状态绑定系统
- **双端支持**: 命令行 CLI 模式 + PySide6/Pygame 图形客户端
- **配置驱动**: 通过 `default_config.json` 灵活调整游戏参数

## 快速开始

### 环境依赖

```bash
pip install -r requirements.txt
```

依赖：`PySide6`、`pygame`

### 命令行模式

```bash
cd include
python main.py
```

### 图形客户端

```bash
python clientgui.py
```

图形客户端通过网络连接游戏服务器，支持石头剪刀布出拳交互与实时战况显示。

### 游戏模式

1. **自定义角色选择**: 从所有可用角色中选择 2~6 个进行对战
2. **默认模式**: 快速开始，使用预设的骑士、召唤师、剑客三方混战

## 现有角色

| ID | 显示名 | 定位 |
|----|--------|------|
| `knight` | 骑士 | 防御型战士，盾技能可回退状态 |
| `summoner` | 召唤师 | 积累召唤物发动强力齐攻 |
| `swordsman` | 剑客 | 近战输出，剑意印记实现连击 |
| `ranger` | 游侠 | 远程灵活，多段攻击 |
| `array_master` | 阵鬼 | 阵法控场，邻接联动 |
| `healer` | 治疗师 | 辅助治疗，团队续航 |
| `scholar` | 魔道学者 | 魔法爆发，知识积累 |
| `oil_master` | 卖油翁 | 范围泼油，持续燃烧 |
| `warlock` | 术士 | 诅咒印记，削弱敌方 |
| `scythe_worker` | 镰刀工 | 收割低血量敌人 |
| `ninja` | 忍者 | 高隐匿，暴击连斩 |
| `mechanic` | 机械师 | 部署机械装置 |
| `disc_master` | 卖光盘的 | 飞碟弹射，多目标 |
| `chicken_master` | 吃鸡大师 | 求生特化，末圈收缩 |
| `scientist` | 科学家 | 实验技能，随机增益 |
| `target` | 靶子 | 测试用靶，无攻击力 |

## 项目结构

```
quanzhi/
├── include/                        # 游戏引擎核心包
│   ├── main.py                     # 游戏主程序入口
│   ├── core/                       # 核心基类模块
│   │   ├── character.py            # 角色基类
│   │   ├── skill.py                # 技能系统
│   │   ├── behavior.py             # 行为类型定义
│   │   ├── player.py               # 玩家类
│   │   ├── summon.py               # 召唤物类
│   │   ├── plugin_interface.py     # 插件接口抽象基类
│   │   └── plugin_schema.py        # 插件数据校验
│   ├── characters/                 # 内置角色实现（16个）
│   ├── systems/                    # 游戏系统模块
│   │   ├── dual_judgment.py        # 双人判定系统
│   │   ├── continuous_effect.py    # 持续效果系统
│   │   └── state_binding.py        # 状态绑定系统
│   ├── factory/                    # 工厂和插件加载模块
│   │   ├── character_factory.py    # 角色工厂与注册表
│   │   ├── character_init.py       # 内置角色注册
│   │   ├── character_selection.py  # 角色选择 UI
│   │   └── plugin_loader.py        # 插件加载器（支持热重载）
│   ├── backend/                    # 游戏后端逻辑
│   │   ├── game_backend.py         # GameBackend 核心类
│   │   └── game_cli.py             # 命令行前端
│   └── config/                     # 配置模块
│       ├── game_config.py          # 配置加载
│       └── default_config.json     # 默认配置
├── clientgui.py                    # PySide6/Pygame 图形客户端
├── tests/                          # 自动化测试
├── CHARACTER_GUIDE.md              # 角色开发指南
└── README.md                       # 本文件
```

## 系统架构

### 后端与前端分离

游戏逻辑封装于 `GameBackend`，CLI 交互由 `GameCLI` 处理，便于接入不同前端：

```python
from backend.game_backend import GameBackend
from backend.game_cli import GameCLI

backend = GameBackend(characters)
cli = GameCLI(backend)
cli.run()
```

### CharacterFactory 工厂模式

```python
from factory.character_factory import get_character_factory

factory = get_character_factory()
knight = factory.create("knight", "我的骑士")
summoner = factory.create("summoner")
```

### 插件系统

在 `plugins/` 目录下放置符合规范的角色模块，游戏启动时自动加载。
也可通过 `setuptools` entry points（组名 `quanzhi.plugins`）发布第三方插件。
支持热重载（可在 `default_config.json` 中开启 `hot_reload`）。

详见 [CHARACTER_GUIDE.md](CHARACTER_GUIDE.md) 了解如何开发自定义角色插件。

### 游戏配置

编辑 `include/config/default_config.json` 调整以下参数：

```json
{
  "game": {
    "max_rounds": 100,
    "min_players": 2,
    "max_players": 6,
    "default_characters": ["knight", "summoner", "swordsman"]
  },
  "plugins": {
    "enabled": true,
    "directory": "plugins",
    "auto_load": true,
    "hot_reload": false
  }
}
```

## 开发

### 运行测试

```bash
pytest tests/
```

### 代码规范

- 使用中文注释和文档字符串
- 遵循 PEP 8 编码规范
- 新角色必须继承 `Character` 基类并导出 `ROLE_ID` 与 `STATS_DATA`
- 使用类型注解提高代码可读性

## 许可证

见 [LICENSE](LICENSE) 文件。

## 贡献

欢迎提交 Pull Request 添加新角色或改进游戏机制！
