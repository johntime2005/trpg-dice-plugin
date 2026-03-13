# TRPG 插件重构方案

## 核心理念：AI 驱动的智能 KP/DM

将 AI 从"工具调用者"升级为"智能游戏主持人"，充分发挥大模型的叙事、即兴创作和情境理解能力。

## 重构模块

### 1. 智能剧情引擎 (core/story_engine.py)

**功能：**
- 动态剧情生成：根据玩家行动生成后续剧情
- 场景描述生成：自动生成沉浸式场景描述
- 剧情分支管理：追踪玩家选择，动态调整剧情走向
- 模组智能解读：理解模组内容，灵活应对玩家偏离

**核心方法：**
```python
async def generate_scene_description(context, location, mood) -> str
async def suggest_plot_development(current_state, player_actions) -> dict
async def adapt_module_content(module_text, player_deviation) -> str
```

### 2. 智能 NPC 系统 (core/npc_manager.py)

**功能：**
- NPC 人格模拟：为每个 NPC 维护独特人格和记忆
- 动态对话生成：根据 NPC 性格和当前情境生成对话
- NPC 行为预测：预测 NPC 在特定情况下的反应
- 关系网络追踪：管理 NPC 之间及与 PC 的关系

**核心方法：**
```python
async def create_npc(name, personality, background, secrets) -> NPC
async def generate_npc_dialogue(npc, context, player_input) -> str
async def predict_npc_reaction(npc, event) -> str
async def update_npc_relationship(npc_id, target_id, change) -> None
```

### 3. 增强提示词系统 (core/enhanced_prompts.py)

**功能：**
- 动态上下文注入：实时分析对话，注入相关信息
- 情绪氛围控制：根据剧情阶段调整 AI 叙事风格
- 玩家画像追踪：学习玩家偏好，个性化体验
- 智能规则裁定：结合规则和情境做出合理裁定

**提示词类型：**
- 剧情阶段提示（开场/调查/高潮/结局）
- 氛围控制提示（恐怖/紧张/轻松/史诗）
- 玩家偏好提示（战斗导向/角色扮演导向/解谜导向）
- 即兴创作指导（如何应对意外情况）

### 4. 智能战报生成器 (core/narrative_report.py)

**功能：**
- 叙事化战报：将数据转化为精彩故事
- 高光时刻提取：识别并强调精彩瞬间
- 角色弧光分析：总结每个角色的成长轨迹
- 多视角叙述：从不同角色视角重述关键事件

**核心方法：**
```python
async def generate_narrative_report(session_data) -> str
async def extract_highlight_moments(events) -> List[dict]
async def analyze_character_arc(character_id, events) -> str
async def generate_multi_perspective(event, characters) -> dict
```

### 5. 情境感知检定系统 (core/contextual_checks.py)

**功能：**
- 智能难度调整：根据剧情重要性动态调整 DC
- 失败后果生成：为失败检定生成有趣的后果
- 成功奖励建议：为成功检定提供合理奖励
- 检定时机判断：AI 自主判断何时需要检定

**核心方法：**
```python
async def suggest_check_difficulty(action, context, importance) -> int
async def generate_failure_consequence(check_type, context) -> str
async def generate_success_reward(check_type, context) -> str
async def should_require_check(action, context) -> bool
```

## 实现优先级

### Phase 1: 核心叙事能力（高优先级）
1. 增强提示词系统 - 让 AI 理解自己的 KP/DM 角色
2. 智能剧情引擎 - 基础场景描述和剧情建议
3. 情境感知检定系统 - 智能难度和后果生成

### Phase 2: NPC 和互动（中优先级）
4. 智能 NPC 系统 - NPC 人格和对话生成
5. 智能战报生成器 - 叙事化战报

### Phase 3: 高级功能（低优先级）
6. 玩家画像系统 - 学习玩家偏好
7. 多模态支持 - 图片生成、语音合成

## 技术要点

### 提示词工程策略
- **分层注入**：基础身份 → 当前状态 → 情境指导 → 即兴创作
- **动态权重**：根据对话阶段调整不同提示词的优先级
- **记忆管理**：使用向量数据库存储长期记忆，避免上下文溢出

### 沙盒方法设计
- **最小化工具调用**：让 AI 自主决策，减少显式工具调用
- **结果导向**：工具返回结果而非指令，让 AI 自由叙述
- **上下文传递**：每个工具调用携带丰富上下文信息

### 数据结构优化
```python
# 剧情状态
PlotState:
  - current_scene: str
  - tension_level: int (1-10)
  - active_npcs: List[NPC]
  - pending_events: List[Event]
  - player_choices: List[Choice]

# NPC 数据
NPC:
  - personality_traits: dict
  - current_mood: str
  - memory: List[Memory]
  - relationships: dict
  - secrets: List[str]
```

## 示例场景

### 传统方式
```
玩家: 我想调查这个房间
AI: 请进行侦察检定
玩家: r 侦察
系统: 🎲 75 成功
AI: 你发现了一个暗门
```

### 重构后
```
玩家: 我想调查这个房间
AI: 你小心翼翼地环视这个布满灰尘的书房。月光透过破碎的窗户洒进来，
    在地板上投下斑驳的光影。你注意到书架上的书籍排列有些不自然...
    
    [自动进行侦察检定: 75 成功]
    
    当你轻轻推动那本《克苏鲁神话》时，整个书架发出低沉的摩擦声，
    缓缓向一侧移开，露出一条通往地下的狭窄楼梯。从黑暗的深处，
    传来若有若无的呢喃声...
    
    你打算怎么做？
```

## 配置项扩展

```python
# AI 行为配置
AI_NARRATIVE_STYLE: str = "immersive"  # immersive/concise/dramatic
AI_PROACTIVITY: int = 7  # 1-10, AI 主动推进剧情的积极度
AUTO_SCENE_DESCRIPTION: bool = True  # 自动生成场景描述
AUTO_NPC_DIALOGUE: bool = True  # 自动生成 NPC 对话
FAILURE_CREATIVITY: int = 8  # 失败后果的创意程度
DYNAMIC_DIFFICULTY: bool = True  # 动态调整检定难度
```

## 兼容性

- 保留所有现有命令和功能
- 新功能通过配置项控制，可选启用
- 渐进式迁移，不破坏现有用户体验
