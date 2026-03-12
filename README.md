# TRPG Dice Plugin

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

一个功能完善的 TRPG 骰子系统插件，为 Nekro Agent 提供专业的跑团支持

[功能特性](#功能特性) • [快速开始](#快速开始) • [使用文档](#使用文档) • [贡献指南](#贡献指南)

</div>

## 📖 简介

TRPG Dice Plugin 是一个综合性的桌面角色扮演游戏（TRPG）辅助系统，参考 OlivaDice 标准设计，支持多种主流 TRPG 规则系统。该插件提供完整的骰子掷骰、角色管理、技能检定、战斗追踪等功能，并集成 AI 驱动的智能游戏主持功能。

### 支持的规则系统

- **克苏鲁的呼唤（Call of Cthulhu）** - 完整的 CoC 7 版规则支持
- **龙与地下城 5E（D&D 5E）** - 包含优势/劣势、先攻、豁免检定等
- **黑暗世界（World of Darkness）** - 骰池系统支持
- **Fate 系统** - Fate 骰子及相关规则
- **通用骰子系统** - 支持各类自定义骰子表达式

## ✨ 功能特性

### 🎲 核心掷骰功能
- **基础掷骰** - 支持复杂骰子表达式（如 `3d6+2d4+5`）
- **优势/劣势** - D&D 5E 优势劣势掷骰系统
- **爆炸骰** - 开放性骰子，掷出最大值继续掷骰
- **隐藏掷骰** - 暗骰功能，只显示最终结果
- **多次掷骰** - 一次性进行多次掷骰操作

### 👤 角色管理系统
- **角色卡创建** - 支持 CoC 和 D&D 5E 角色卡
- **属性管理** - 完整的属性和技能值设置
- **角色切换** - 多角色卡管理和切换
- **自动生成** - 随机角色生成器（符合规则标准）
- **数据持久化** - 角色数据自动保存

### ⚔️ 战斗与检定
- **技能检定** - 支持各类技能检定和对抗检定
- **先攻追踪** - 战斗先攻顺序管理
- **生命值管理** - HP 增减和状态追踪
- **理智检定** - CoC 理智值系统
- **豁免检定** - D&D 各类豁免

### 🤖 AI 增强功能
- **智能角色构建** - AI 辅助创建角色背景故事
- **动态剧情提示** - 根据游戏进程提供剧情建议
- **战报生成** - 自动生成精彩的战斗报告
- **文档管理** - 游戏文档和资料存储

### 🎨 辅助工具
- **随机姓名生成** - 中英文姓名随机生成
- **疯狂症状表** - CoC 疯狂症状随机生成
- **今日人品** - 基于日期的人品检定
- **抽卡功能** - 标准扑克牌抽取

## 🚀 快速开始

### 环境要求

- Python 3.8+
- Nekro Agent 框架
- 必要的 Python 依赖包

### 安装步骤

1. **克隆仓库**
```bash
git clone https://github.com/yourusername/trpg-dice-plugin.git
cd trpg-dice-plugin
```

2. **放置插件**
将插件目录复制到 Nekro Agent 的插件目录：
```bash
cp -r trpg-dice-plugin /path/to/nekro-agent/plugins/builtin/
```

3. **重启 Nekro Agent**
重启机器人以加载插件

### 基础使用

```bash
# 简单掷骰
r d20+5           # 掷一个 20 面骰子加 5

# 创建角色卡
st new 艾莉娅 CoC  # 创建 CoC 系统角色卡

# 技能检定
ra 侦察 65        # 进行侦察技能检定

# 优势掷骰
adv +3            # 优势 d20+3

# 查看帮助
help trpg         # 查看完整帮助
```

## 📚 使用文档

### 基础指令速查

| 分类 | 指令 | 说明 |
|------|------|------|
| **掷骰** | `r <表达式>` | 基础掷骰 |
| | `rh <表达式>` | 隐藏掷骰 |
| | `adv [修正]` | 优势掷骰 |
| | `dis [修正]` | 劣势掷骰 |
| **检定** | `ra <技能> [值]` | 技能检定 |
| | `coc <值> [难度]` | CoC 检定 |
| | `san <理智> <损失>` | 理智检定 |
| **角色** | `st` | 显示角色卡 |
| | `st new <名字> [系统]` | 创建角色 |
| | `st <属性> <值>` | 设置属性 |
| | `hp [操作]` | 生命值管理 |

### 详细文档

- [完整使用手册](docs/trpg_dice_help.md) - 所有指令的详细说明
- [战报系统指南](docs/battle_report_guide.md) - 战报生成和使用
- [AI 提示工程](docs/trpg_prompt_examples.md) - AI 功能使用示例
- [开发者文档](docs/development.md) - 插件开发和扩展

## 🏗️ 项目结构

```
trpg-dice-plugin/
├── plugin.py                    # 主插件入口
├── __init__.py                  # 包初始化
├── core/                        # 核心功能模块
│   ├── dice_engine.py          # 骰子引擎
│   ├── character_manager.py    # 角色管理
│   ├── ai_character_builder.py # AI 角色构建
│   ├── document_manager.py     # 文档管理
│   ├── battle_report.py        # 战报系统
│   └── prompt_injection.py     # AI 提示注入
├── templates/                   # 角色卡模板
│   ├── coc7_template.json      # CoC 7版模板
│   └── dnd5e_template.json     # D&D 5E模板
└── docs/                        # 文档目录
    ├── trpg_dice_help.md       # 使用手册
    ├── battle_report_guide.md  # 战报指南
    ├── trpg_prompt_examples.md # AI 示例
    └── development.md          # 开发文档
```

## 🎯 使用示例

### 场景一：创建 CoC 角色并进行检定

```bash
# 1. 创建 CoC 角色
st new 调查员张三 CoC

# 2. 设置属性
st 力量 65
st 敏捷 70
st 侦察 75

# 3. 进行侦察检定
ra 侦察

# 4. 遇到怪物，进行理智检定
san 65 1/1d6
```

### 场景二：D&D 5E 战斗

```bash
# 1. 创建角色
st new 战士艾莉娅 DnD5e

# 2. 先攻检定
init +2

# 3. 优势攻击
adv +5

# 4. 受到伤害
hp -12

# 5. 体质豁免
save 体质 熟练
```

### 场景三：快速随机角色生成

```bash
# 生成 CoC 角色（包含随机属性、职业、年龄）
cocchar

# 生成 D&D 角色（包含随机种族、职业、属性）
dndchar

# 生成随机姓名
name 女 3
```

## 🔧 配置选项

插件支持以下可配置项：

```python
MAX_DICE_COUNT = 100        # 单次最大骰子数量
MAX_DICE_SIDES = 1000       # 骰子最大面数
DEFAULT_DICE_TYPE = 'd20'   # 默认骰子类型
ENABLE_CRITICAL_EFFECTS = True  # 启用大成功/大失败
AUTO_SAVE_CHARACTERS = True     # 自动保存角色数据
```

## 🤝 贡献指南

欢迎贡献代码、报告问题或提出新功能建议！

### 贡献流程

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 代码规范

- 遵循 PEP 8 Python 代码规范
- 使用类型注解提高代码可读性
- 添加必要的文档字符串和注释
- 确保所有测试通过

## 📝 开发路线图

- [x] 基础骰子系统
- [x] CoC 规则支持
- [x] D&D 5E 规则支持
- [x] 角色卡管理
- [x] AI 角色构建
- [x] 战报系统
- [ ] 更多规则系统支持（Pathfinder、GURPS）
- [ ] Web 界面
- [ ] 在线多人协作
- [ ] 语音识别骰子指令

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

## 👥 作者

- **johntime** --开发者

## 🙏 致谢

- 感谢 [OlivaDice](https://github.com/OlivOS-Team/OlivaDice) 项目提供的设计参考
- 感谢 Nekro Agent 框架的支持
- 感谢所有为本项目做出贡献的开发者

## 📮 联系方式

- 提交 Issue：[GitHub Issues](https://github.com/yourusername/trpg-dice-plugin/issues)
- 讨论区：[GitHub Discussions](https://github.com/yourusername/trpg-dice-plugin/discussions)

---

<div align="center">

**如果觉得这个项目有帮助，请给它一个 ⭐ Star！**

Made with ❤️ by TRPG enthusiasts

</div>
