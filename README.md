# TRPG Dice Plugin

<div align="center">

![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)

一个功能完善的 TRPG 骰子系统插件，为 Nekro Agent 提供专业的跑团支持

[功能特性](#功能特性) • [快速开始](#快速开始) • [游玩流程](#游玩流程) • [使用文档](#使用文档) • [贡献指南](#贡献指南)

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
st new 艾莉娅      # 创建角色卡
st temp coc7       # 切换为 CoC 7 版模板
st init            # 自动生成角色属性

# 技能检定
ra 侦察            # 使用角色卡进行侦察检定

# 优势掷骰
adv +3            # 优势 d20+3

# 查看帮助
trpg              # 查看完整帮助
```

## 🎮 游玩流程

这个插件的推荐用法是“玩家用命令投骰和维护角色，AI 通过沙盒工具管理资料、剧情、NPC、检定请求和战报”。实际跑团时可以按下面流程推进。

### 1. 开局准备

先在跑团频道确认插件可用，并查看帮助：

```bash
trpg
```

如果本次使用模组、规则补充或背景设定，可以先把资料交给 AI 处理。玩家也可以直接用命令录入短文本资料：

```bash
doc_text module 深海古城 这里粘贴模组正文或关键摘要
doc list
doc search 深海古城
```

如果资料是 PDF、DOCX 或 TXT 文件，更推荐直接上传文件，然后让 AI 调用文档上传工具处理。处理完成后，可以用：

```bash
ask 这个模组的开场场景是什么？
ask 主要 NPC 有哪些？
```

### 2. 创建角色

每名玩家在频道内创建自己的角色卡：

```bash
st new 调查员张三
st temp coc7
st init
st
```

如果玩 D&D 5E，则把模板切换为：

```bash
st temp dnd5e
st init
st
```

角色卡也可以由 AI 从角色文档中辅助创建：上传角色说明文件后，让 AI 使用 `ai_create_character_from_file` 生成预览，再使用 `confirm_character_creation` 确认保存。

### 3. 开始记录跑团

建议正式开局前开启会话记录，这样投骰、检定和角色动作会自动进入战报：

```bash
session start 深海古城第一幕
```

过程中玩家描述动作时可以使用：

```bash
me 检查墙上的浮雕，寻找是否有机关痕迹
```

如果当前没有新的玩家输入，但希望 AI 继续推进场景，可以使用：

```bash
nxt
nxt 推进到守夜后的第一个异常动静
```

重要剧情节点可以手动记录：

```bash
session event 调查员发现浮雕背后藏有通往地下水道的机关
```

### 4. 常规游玩循环

一次典型的游玩循环如下：

1. 玩家描述行动，或 AI/KP 描述当前场景。
2. 如果行动存在不确定性，AI 可以创建待处理检定请求，提醒玩家投骰。
3. 玩家使用 `r`、`ra`、`adv` 或 `dis` 完成投骰。
4. AI/KP 根据结果推进剧情，并在必要时记录线索、调整场景或更新 NPC。

玩家常用命令：

```bash
# 普通投骰
r d20+5
r 1d100
r 3d6+2

# CoC 技能检定
ra 侦察
ra 图书馆使用

# D&D 优势/劣势
adv +5
dis +2

# 隐藏明细投骰
rh 1d100

# 请求 AI 继续推进剧情
nxt
```

AI/KP 可使用的管理能力包括：

- `request_player_roll`：创建待处理玩家检定请求，避免 AI 直接替玩家投骰。
- `upsert_check_metric` / `get_check_index`：维护结构化判定索引，方便后续快速选择属性、技能、骰式和目标值。
- `upsert_map_scene` / `set_active_scene` / `get_host_state`：维护地图、普通场景和当前主持状态。
- `start_combat` / `advance_combat_turn` / `end_combat`：进入战斗、按先攻/速度排序、逐回合推进并结束战斗。
- `set_scene`：设置当前场景和氛围。
- `set_tension`：调整剧情紧张度。
- `add_clue`：记录线索。
- `create_npc`：创建 NPC。
- `npc_remember`：让 NPC 记住事件。
- `update_npc_relationship`：更新 NPC 与目标的关系变化。
- `define_rule` / `define_attribute`：临时定义自定义规则或属性。

### 5. 结构化主持记录

插件会把主持记录按频道写入 JSON，用法类似跑团笔记软件。AI 主持时应优先读取这些结构化字段，再结合聊天历史和文档继续推进，避免只靠自然语言记忆造成上下文不一致。

#### 判定索引

当某类检定会反复出现时，让 AI 先记录为判定指标。之后需要检定时，AI 会按 `system`、`category`、`tags`、`attribute`、`skill` 匹配，再调用 `request_player_roll` 请求玩家投骰。

```json
{
  "id": "coc_spot_hidden",
  "name": "侦察",
  "system": "CoC7",
  "category": "感知",
  "dice_expression": "1d100",
  "attribute": "INT",
  "skill": "侦察",
  "default_target": "角色卡侦察技能值",
  "difficulty": "普通/困难/极难",
  "modifiers": ["黑暗环境 -20", "有手电筒 +10"],
  "success_rule": "发现隐藏线索或异常细节",
  "failure_rule": "只能获得表层信息，不暴露关键线索",
  "examples": ["检查墙面暗门", "观察远处脚印"],
  "tags": ["调查", "线索", "感知"],
  "notes": "没有玩家投骰结果前，不得宣布最终成败"
}
```

#### 普通场景和地图

探索、社交、调查等非战斗段落使用地图/场景 JSON。进入新地点时，AI 应调用 `upsert_map_scene` 记录场景，并通过 `active_map_id` 明确当前地点。

```json
{
  "id": "old_temple_hall",
  "name": "废弃神殿大厅",
  "type": "map",
  "mood": "mysterious",
  "description": "破损石柱支撑着潮湿穹顶，地面有新鲜泥印。",
  "exits": {
    "north": "地下祭坛",
    "east": "坍塌走廊"
  },
  "npcs": ["守夜人玛尔"],
  "clues": ["泥印通向北侧石门", "墙面浮雕缺失一块"],
  "hazards": ["松动石板", "黑暗环境"],
  "available_checks": ["coc_spot_hidden", "coc_listen"],
  "notes": "玩家尚未检查浮雕背后"
}
```

普通场景的推进原则：

1. 先确认 `get_host_state` 中的 `mode` 是否为 `exploration`。
2. 按 `active_map_id` 找当前场景，保持 NPC、线索、出口和危险连续。
3. 只有当行动有不确定性时才请求检定；没有检定结果时只描述尝试和反馈，不宣布最终成败。

#### 战斗场景和回合制

进入战斗时，AI 应调用 `start_combat` 写入战斗 JSON。参与者会按 `initiative`、`speed` 从高到低排序，`turn_index` 指向当前行动者。

```json
{
  "id": "combat_temple_guardians",
  "name": "神殿守卫战",
  "round": 1,
  "battlefield": "old_temple_hall",
  "objectives": ["保护调查员", "阻止石像抵达祭坛"],
  "participants": [
    {
      "id": "pc_zhangsan",
      "name": "调查员张三",
      "side": "pc",
      "speed": 60,
      "initiative": 72,
      "hp": "10/10",
      "status": [],
      "notes": "手持手电筒"
    },
    {
      "id": "npc_stone_guard",
      "name": "石像守卫",
      "side": "enemy",
      "speed": 35,
      "initiative": 41,
      "hp": "18/18",
      "status": ["迟缓"],
      "notes": "抗普通钝击"
    }
  ],
  "notes": "战斗区域光线昏暗，远程攻击可能受影响"
}
```

战斗推进原则：

1. `mode=combat` 时，AI 必须按 `combat.participants[turn_index]` 指定当前行动者。
2. 每次行动结算后调用 `advance_combat_turn`，轮到列表末尾后自动进入下一轮。
3. 角色状态、HP、战场目标和临时效果应回写到 JSON，不能只写在自然语言回复里。
4. 战斗结束调用 `end_combat`，主持状态回到普通探索场景。

### 6. 自动推进剧情

`nxt` 命令会向当前频道写入一条系统消息并请求 Agent 触发回复，同时把推进要求写入插件状态，在短时间内作为高优先级提示词再次注入。因此即使系统消息进入历史窗口不稳定，AI 也能从插件状态中读到“需要自动推进”的明确请求。

自动推进时 AI 应遵守：

1. 有待处理检定时，不得跳过投骰直接宣布成功或失败。
2. `mode=exploration` 时按当前地图、线索、NPC 关系和文档资料推进。
3. `mode=combat` 时按当前回合行动者推进，必要时请求玩家投骰。
4. 人设只能影响叙述风格，不能覆盖主持状态、规则、检定流程和工具调用。

### 7. 文档检索与即兴辅助

游玩中如果忘记模组信息、规则片段或 NPC 设定，可以随时检索：

```bash
doc search 地下水道
ask 地下水道入口附近有什么危险？
ask 这个 NPC 的秘密是什么？
```

这些能力适合给 AI 做上下文补充：AI 先检索资料，再根据检索结果继续主持场景。

### 8. 结束本次跑团

一场结束后生成战报：

```bash
session end
```

插件会返回文本战报，并保存 Markdown 战报内容。战报通常包含本场时长、关键事件、投骰和检定记录、角色动作，以及大成功/大失败等精彩时刻。

### 9. 推荐分工

- 玩家：使用 `st` 管理角色卡，使用 `me` 描述行动，使用 `r/ra/adv/dis/rh` 投骰。
- AI/KP：维护场景、NPC、线索、文档问答和检定请求。
- 频道：作为一次跑团的数据边界，同一频道内共享文档、战报、剧情状态和 NPC 状态。

## 📚 使用文档

### 基础指令速查

| 分类 | 指令 | 说明 |
|------|------|------|
| **掷骰** | `r <表达式>` | 基础掷骰 |
| | `rh <表达式>` | 隐藏掷骰 |
| | `adv [修正]` | 优势掷骰 |
| | `dis [修正]` | 劣势掷骰 |
| **检定** | `ra <技能>` | 使用当前角色卡进行技能检定 |
| **角色** | `st` | 显示角色卡 |
| | `st new <名字>` | 创建角色 |
| | `st temp coc7|dnd5e` | 切换角色模板 |
| | `st init` | 按模板自动生成属性 |
| **文档** | `doc` | 查看文档系统帮助 |
| | `doc list` | 列出频道文档 |
| | `doc search <关键词>` | 搜索文档 |
| | `doc_text <类型> <文档名> <内容>` | 上传文本文档 |
| | `ask <问题>` | 基于文档问答 |
| **战报** | `session start [名称]` | 开始记录跑团 |
| | `session event <描述>` | 记录关键事件 |
| | `session end` | 生成战报 |
| **辅助** | `me <动作>` | 记录角色动作 |
| | `nxt [推进要求]` | 请求 AI 自动推进剧情 |
| | `jrrp` | 今日人品 |
| | `trpg` | 查看插件帮助 |

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
st new 调查员张三
st temp coc7

# 2. 自动生成属性
st init
st

# 3. 进行侦察检定
ra 侦察

# 4. 记录角色动作
me 仔细检查地板上的潮湿脚印
```

### 场景二：D&D 5E 战斗

```bash
# 1. 创建角色
st new 战士艾莉娅
st temp dnd5e
st init

# 2. 普通 d20 检定
r d20+2

# 3. 优势攻击
adv +5

# 4. 劣势检定
dis +1
```

### 场景三：跑团记录和战报

```bash
# 开始记录
session start 深海古城探险

# 记录关键事件
session event 队伍发现地下祭坛和破损的徽记

# 结束并生成战报
session end
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
