"""
增强提示词系统 - 动态上下文感知的 AI 行为指导
"""

from typing import Optional
from .story_engine import StoryEngine, TensionLevel, SceneMood


async def inject_narrative_guidance(_ctx, story_engine: StoryEngine) -> str:
    """注入叙事风格指导"""
    
    plot_state = await story_engine.get_plot_state(_ctx.chat_key)
    
    tension_guidance = {
        TensionLevel.CALM: "保持轻松自然的叙述，给玩家探索空间",
        TensionLevel.CURIOUS: "用细节描写激发好奇心，暗示有趣的发现",
        TensionLevel.TENSE: "加快节奏，使用短句，营造紧张感",
        TensionLevel.DANGEROUS: "强调危险信号，让玩家感受到威胁",
        TensionLevel.CRITICAL: "高度紧张的描写，每个决定都至关重要"
    }
    
    mood_guidance = {
        SceneMood.PEACEFUL: "温暖平和的氛围，注重日常细节",
        SceneMood.MYSTERIOUS: "神秘莫测，多用暗示和象征",
        SceneMood.HORROR: "恐怖压抑，调动感官描写制造不安",
        SceneMood.EPIC: "宏大壮阔，英雄主义色彩",
        SceneMood.MELANCHOLY: "忧郁感伤，注重情感共鸣"
    }
    
    parts = [
        "# 叙事指导",
        f"当前场景: {plot_state.current_scene}",
        f"紧张度: {tension_guidance.get(plot_state.tension_level, '')}",
        f"氛围: {mood_guidance.get(plot_state.scene_mood, '')}"
    ]
    
    if plot_state.active_clues:
        parts.append(f"已发现线索: {', '.join(plot_state.active_clues[:3])}")
    
    return "\n".join(parts)


async def inject_improvisation_guide(_ctx) -> str:
    """注入即兴创作指导"""
    
    return """# 即兴创作原则

当玩家行动超出预期时:
• 说"是，而且..." - 接受玩家创意并扩展
• 将意外转化为剧情机会
• 保持内部逻辑一致性
• 让失败变得有趣而非惩罚

场景描述要点:
• 调动五感 - 视觉、听觉、触觉、嗅觉
• 先环境后细节 - 由大到小引导注意力
• 暗示而非直说 - 让玩家自己发现
• 为行动留白 - 描述后询问玩家意图"""


async def inject_check_philosophy(_ctx) -> str:
    """注入检定哲学"""
    
    return """# 检定原则

何时要求检定:
• 有意义的失败可能 - 失败会带来有趣后果
• 时间压力或资源消耗 - 检定本身有成本
• 不确定的结果 - 成功失败都能推进剧情

执行约束（必须遵守）:
• 你只能提出“请玩家投骰”的请求，不能自行生成随机结果
• 所有检定结果必须来自玩家命令返回（如 r / ra / adv / dis / rh）
• 在收到命令结果前，禁止叙述“成功/失败/点数”

何时不需要检定:
• 角色擅长且无压力 - 专业人士做本职工作
• 失败无趣 - 只会卡住剧情
• 已经付出代价 - 玩家的聪明方案应该奏效

失败的艺术:
• 失败≠无进展 - 给予部分信息或新线索
• 失败=复杂化 - 目标达成但带来新问题
• 失败=代价 - 成功但付出意外代价"""


async def inject_dynamic_difficulty(_ctx, story_engine: StoryEngine) -> str:
    """注入动态难度指导"""
    
    plot_state = await story_engine.get_plot_state(_ctx.chat_key)
    
    if plot_state.tension_level.value >= 7:
        return """# 难度调整: 高压场景
• 提高检定难度，强调风险
• 失败后果更严重
• 时间限制更紧迫"""
    elif plot_state.tension_level.value <= 3:
        return """# 难度调整: 探索场景  
• 降低检定难度，鼓励尝试
• 失败提供线索而非惩罚
• 给予充足思考时间"""
    
    return ""


async def inject_npc_interaction_guide(_ctx) -> str:
    """注入 NPC 互动指导"""
    
    return """# NPC 互动原则

赋予 NPC 生命:
• 每个 NPC 有独特说话方式和动作习惯
• NPC 有自己的目标和动机，不只是信息源
• NPC 会记住之前的互动
• NPC 对 PC 的态度会变化

对话技巧:
• 用方言、口头禅、语气词区分角色
• 通过对话展示性格而非直接描述
• NPC 可以撒谎、隐瞒、误解
• 让 NPC 主动提问，推动对话"""


def register_enhanced_prompts(plugin, story_engine: StoryEngine, custom_rules=None, rule_modeler=None):
    
    @plugin.mount_prompt_inject_method(
        name="narrative_guidance",
        description="根据剧情状态动态调整叙事风格"
    )
    async def _inject_narrative(_ctx) -> str:
        return await inject_narrative_guidance(_ctx, story_engine)
    
    @plugin.mount_prompt_inject_method(
        name="improvisation_guide",
        description="即兴创作和场景描述指导"
    )
    async def _inject_improv(_ctx) -> str:
        return await inject_improvisation_guide(_ctx)
    
    @plugin.mount_prompt_inject_method(
        name="check_philosophy",
        description="智能检定时机和失败处理哲学"
    )
    async def _inject_checks(_ctx) -> str:
        return await inject_check_philosophy(_ctx)
    
    @plugin.mount_prompt_inject_method(
        name="dynamic_difficulty",
        description="根据剧情紧张度动态调整难度"
    )
    async def _inject_difficulty(_ctx) -> str:
        return await inject_dynamic_difficulty(_ctx, story_engine)
    
    @plugin.mount_prompt_inject_method(
        name="npc_interaction",
        description="NPC 互动和对话生成指导"
    )
    async def _inject_npc(_ctx) -> str:
        return await inject_npc_interaction_guide(_ctx)
    
    if custom_rules:
        @plugin.mount_prompt_inject_method(
            name="custom_rules",
            description="注入自定义规则和属性"
        )
        async def _inject_custom(_ctx) -> str:
            return await custom_rules.get_custom_rules_prompt(_ctx.chat_key)
    
    if rule_modeler:
        @plugin.mount_prompt_inject_method(
            name="intelligent_rules",
            description="AI 智能理解和应用规则"
        )
        async def _inject_intelligent(_ctx) -> str:
            from .intelligent_prompts import inject_intelligent_rule_system
            return await inject_intelligent_rule_system(_ctx, rule_modeler)
