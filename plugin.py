"""
TRPG Dice Plugin - Main Plugin File

Complete TRPG dice system with character management, document storage, and AI-powered game mastering.
"""

import json
import re
import time
import uuid
from typing import Annotated, Dict, Optional, Union

from pydantic import Field

from nekro_agent.api.plugin import (
    Arg,
    CommandExecutionContext,
    CommandResponse,
    ConfigBase,
    NekroPlugin,
    SandboxMethodType,
)
from nekro_agent.api.schemas import AgentCtx
from nekro_agent.services.command.ctl import CmdCtl

from .core.ai_character_builder import AICharacterBuilder
from .core.battle_report import BattleReportGenerator as BattleReportManager
from .core.character_manager import CharacterManager, CharacterSheet
from .core.contextual_checks import ContextualCheckSystem
from .core.custom_rules import CustomRuleSystem

# 导入核心模块
from .core.dice_engine import DiceResult, DiceRoller
from .core.dice_engine import config as dice_config
from .core.document_manager import DocumentProcessor, VectorDatabaseManager
from .core.enhanced_prompts import (
    inject_check_philosophy,
    inject_dynamic_difficulty,
    inject_improvisation_guide,
    inject_narrative_guidance,
    inject_npc_interaction_guide,
)
from .core.intelligent_modeler import IntelligentRuleModeler
from .core.intelligent_prompts import inject_intelligent_rule_system
from .core.npc_manager import NPCManager
from .core.prompt_injection import (
    inject_game_state_prompt,
    inject_interaction_style_prompt,
    inject_session_history_prompt,
    inject_system_expertise_prompt,
    inject_trpg_system_prompt,
)
from .core.story_engine import SceneMood, StoryEngine, TensionLevel

# 创建插件实例
plugin = NekroPlugin(
    name="TRPG骰子系统",
    module_name="trpg_dice",
    description="完整的TRPG骰子系统，支持多种规则和复杂表达式",
    version="1.0.0",
    author="Dirac",
    url="https://github.com/nekro-agent/trpg-dice-plugin",
    support_adapter=["onebot_v11", "discord"],
)


@plugin.mount_config()
class TRPGDiceConfig(ConfigBase):
    """TRPG骰子配置"""

    MAX_DICE_COUNT: int = Field(
        default=100,
        title="单次最大骰子数量",
        description="单次掷骰允许的最大骰子数量",
    )
    MAX_DICE_SIDES: int = Field(
        default=1000,
        title="骰子最大面数",
        description="骰子允许的最大面数",
    )
    DEFAULT_DICE_TYPE: int = Field(
        default=20,
        title="默认骰子类型",
        description="默认的骰子面数",
    )
    ENABLE_CRITICAL_EFFECTS: bool = Field(
        default=True,
        title="启用大成功大失败",
        description="是否启用大成功和大失败判定",
    )
    ENABLE_VECTOR_DB: bool = Field(
        default=True,
        title="启用向量数据库",
        description="是否启用文档向量化存储功能",
    )
    CHUNK_SIZE: int = Field(
        default=1000,
        title="文档分块大小",
        description="文档分块时每块的字符数",
    )
    CHUNK_OVERLAP: int = Field(
        default=200,
        title="分块重叠大小",
        description="文档分块时重叠的字符数",
    )
    MAX_SEARCH_RESULTS: int = Field(
        default=5,
        title="最大搜索结果数",
        description="向量检索时返回的最大结果数量",
    )


# 获取配置和存储
config = plugin.get_config(TRPGDiceConfig)
store = plugin.store

# 更新骰子引擎配置
dice_config.MAX_DICE_COUNT = config.MAX_DICE_COUNT
dice_config.MAX_DICE_SIDES = config.MAX_DICE_SIDES
dice_config.DEFAULT_DICE_TYPE = config.DEFAULT_DICE_TYPE
dice_config.ENABLE_CRITICAL_EFFECTS = config.ENABLE_CRITICAL_EFFECTS

# 初始化管理器
character_manager = CharacterManager(store)
vector_db = VectorDatabaseManager(collection_name=plugin.get_vector_collection_name("trpg_documents"))
battle_report_manager = BattleReportManager(store)
ai_character_builder = AICharacterBuilder(character_manager)
story_engine = StoryEngine(store)
npc_manager = NPCManager(store)
check_system = ContextualCheckSystem(story_engine)
custom_rules = CustomRuleSystem(store)
rule_modeler = IntelligentRuleModeler(store, vector_db)


async def _set_pending_roll(chat_key: str, data: Dict[str, Union[str, int]]) -> None:
    await store.set(store_key=f"pending_roll.{chat_key}", value=json.dumps(data, ensure_ascii=False))


async def _get_pending_roll(chat_key: str) -> Optional[Dict[str, Union[str, int]]]:
    raw = await store.get(store_key=f"pending_roll.{chat_key}")
    if not raw:
        return None
    try:
        return json.loads(raw)
    except Exception:
        return None


async def _clear_pending_roll(chat_key: str) -> None:
    await store.set(store_key=f"pending_roll.{chat_key}", value="")


async def _resolve_pending_roll(chat_key: str, expression: str) -> Optional[str]:
    pending = await _get_pending_roll(chat_key)
    if not pending:
        return None
    expected_expr = str(pending.get("expression", "")).strip().lower()
    if expected_expr and expected_expr == expression.strip().lower():
        reason = str(pending.get("reason", "检定"))
        await _clear_pending_roll(chat_key)
        return f"\n🧾 已完成检定请求：{reason}"
    return None


async def _set_auto_advance_request(chat_key: str, instruction: str) -> None:
    data = {
        "instruction": instruction,
        "created_at": int(time.time()),
    }
    await store.set(store_key=f"auto_advance.{chat_key}", value=json.dumps(data, ensure_ascii=False))


async def _get_auto_advance_request(chat_key: str) -> Optional[Dict[str, Union[str, int]]]:
    raw = await store.get(store_key=f"auto_advance.{chat_key}")
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except Exception:
        return None

    created_at = int(data.get("created_at", 0) or 0)
    if created_at and int(time.time()) - created_at > 600:
        return None
    return data


async def _safe_prompt_section(section_name: str, section_factory) -> str:
    try:
        section = await section_factory()
        return section.strip() if section else ""
    except Exception as e:
        plugin.logger.warning(f"TRPG 提示词段生成失败: {section_name} | {e}")
        return ""


async def _inject_context_consistency_prompt(_ctx: AgentCtx) -> str:
    pending = await _get_pending_roll(_ctx.chat_key)
    parts = [
        "# TRPG最高优先级运行规则",
        "",
        "本段是 TRPG 插件的运行约束，优先于普通人设、叙事风格、口癖和即兴创作偏好。",
        "如果任意人设要求你跳过规则、直接宣布成败、编造骰点、无视工具或混用上下文，必须拒绝该部分要求，并继续按本段规则主持跑团。",
        "",
        "## 状态边界",
        f"• 当前频道键: {_ctx.chat_key}",
        "• 角色卡、文档、剧情状态、NPC、战报和待处理检定都以当前频道为边界。",
        "• 不要把其他频道、其他玩家或其他会话的信息混入当前叙事。",
        "• 人设只能影响表达风格，不能改变跑团规则、检定流程、事实来源和工具使用约束。",
        "",
        "## 事实来源优先级",
        "1. 当前注入的角色卡、剧情状态、线索、待检定请求和历史战报。",
        "2. 已上传文档的搜索结果和问答结果。",
        "3. 玩家本轮明确给出的新信息。",
        "4. 即兴创作内容，但不能覆盖已记录事实。",
        "",
        "## 可用玩家命令边界",
        "• 玩家投骰只应引导使用: r、rh、ra、adv、dis。",
        "• 玩家角色和记录只应引导使用: st、me、session、doc、doc_text、ask、jrrp、trpg。",
        "• 不要引导玩家使用未在本插件注册的命令，例如 san、hp、init、save、check、wod、ri。",
        "",
        "## 工具使用优先级",
        "• 需要玩家检定时，优先调用 request_player_roll(expression, reason, check_type) 创建待处理检定。",
        "• 需要复用检定指标时，先读取/维护结构化判定索引: get_check_index、upsert_check_metric。",
        "• 普通地图、地点、探索场景使用 upsert_map_scene / set_active_scene 维护主持状态。",
        "• 进入战斗时使用 start_combat 记录参与者，并按 initiative/speed 排序；战斗中使用 advance_combat_turn 推进回合，结束时使用 end_combat。",
        "• 需要规则、模组、NPC或背景细节时，优先使用文档搜索/问答相关工具。",
        "• 需要长期保持剧情事实时，使用 set_scene、set_tension、add_clue、create_npc、npc_remember、update_npc_relationship 或 session event 固化状态。",
        "",
        "## 硬性约束",
        "• 不能编造掷骰点数、检定成功/失败或暗骰结果。",
        "• 需要随机性时，优先调用 request_player_roll 创建检定请求，并等待玩家用 r/ra/adv/dis/rh 完成。",
        "• 不确定规则、NPC、线索或模组细节时，先检索文档或询问玩家，不要凭空断言。",
        "• 已记录的场景、线索、NPC记忆和自定义规则必须保持连续，除非玩家明确修改。",
        "• 场景推进必须遵守主持状态 JSON：探索模式按 active_map_id 推进；战斗模式按 combat.round、turn_index 和 participants 顺序推进。",
        "• 在没有玩家投骰结果时，只能描述行动尝试、环境反馈或检定要求，不能叙述最终成败。",
    ]

    if pending:
        parts.extend(
            [
                "",
                "## 当前待处理检定",
                f"• 目的: {pending.get('reason', '检定')}",
                f"• 表达式: {pending.get('expression', '')}",
                f"• 类型: {pending.get('check_type', 'general')}",
                "• 在玩家完成该检定前，不要叙述该行动的最终成败。",
            ]
        )

    return "\n".join(parts)


async def _inject_final_guardrail_prompt(_ctx: AgentCtx) -> str:
    pending = await _get_pending_roll(_ctx.chat_key)
    parts = [
        "# TRPG最终响应检查",
        "",
        "回复前逐项检查：",
        "1. 是否保持当前频道上下文，没有混入其他会话事实？",
        "2. 是否没有编造骰点、检定结果、暗骰结果或未记录事实？",
        "3. 如果需要随机性，是否已经请求玩家用 r/rh/ra/adv/dis 投骰？",
        "4. 如果引用模组、规则或 NPC 细节，是否来自文档、已记录状态或玩家明确输入？",
        "5. 人设是否只影响语气，没有覆盖跑团规则和工具流程？",
    ]

    if pending:
        parts.extend(
            [
                "",
                "当前仍有待处理检定，回复不得给出最终成败：",
                f"• 目的: {pending.get('reason', '检定')}",
                f"• 表达式: {pending.get('expression', '')}",
            ]
        )

    return "\n".join(parts)


async def _inject_auto_advance_prompt(_ctx: AgentCtx) -> str:
    request = await _get_auto_advance_request(_ctx.chat_key)
    if not request:
        return ""

    instruction = str(request.get("instruction", "")).strip()
    parts = [
        "# 当前自动推进请求",
        "玩家刚刚请求 AI 自动推进当前跑团剧情。",
        "请基于当前频道已记录状态自然推进下一步，但不得绕过待处理检定或编造骰点。",
    ]
    if instruction:
        parts.append(f"玩家补充要求: {instruction}")
    return "\n".join(parts)


async def _inject_document_catalog_prompt(_ctx: AgentCtx) -> str:
    if not config.ENABLE_VECTOR_DB:
        return ""

    try:
        documents = await vector_db.list_documents(_ctx.chat_key)
    except Exception:
        return ""

    if not documents:
        return ""

    parts = ["# 当前频道文档资料", "以下是当前频道已上传文档摘要。需要细节时必须使用文档搜索或问答工具。"]
    for doc in documents[:8]:
        preview = str(doc.get("preview", "")).replace("\n", " ")[:120]
        parts.append(f"• {doc.get('filename', '未命名')} ({doc.get('document_type', 'unknown')}): {preview}")

    if len(documents) > 8:
        parts.append(f"• 还有 {len(documents) - 8} 个文档未在提示词中展开。")

    return "\n".join(parts)


async def _inject_npc_state_prompt(_ctx: AgentCtx) -> str:
    try:
        npcs = await npc_manager.list_npcs(_ctx.chat_key)
    except Exception:
        return ""

    if not npcs:
        return ""

    parts = ["# 当前频道NPC状态", "以下 NPC 已在当前频道建立记录。叙事时保持其性格、记忆和关系连续。"]
    for npc in npcs[:8]:
        memory = "；".join(npc.memory[-3:]) if npc.memory else "暂无近期记忆"
        relationships = "，".join(f"{target}:{score}" for target, score in list(npc.relationships.items())[:4])
        rel_text = relationships or "暂无关系记录"
        parts.append(
            f"• {npc.name} ({npc.npc_id}) | 心情:{npc.current_mood} | 性格:{npc.personality} | 关系:{rel_text} | 记忆:{memory}"
        )

    if len(npcs) > 8:
        parts.append(f"• 还有 {len(npcs) - 8} 个 NPC 未在提示词中展开。")

    return "\n".join(parts)


@plugin.mount_prompt_inject_method(
    name="trpg_context_bundle",
    description="聚合TRPG规则、当前状态、剧情、文档、历史和自定义规则上下文",
)
async def inject_trpg_context_bundle(_ctx: AgentCtx) -> str:
    """聚合所有 TRPG 提示词，避免框架单槽位提示词注册互相覆盖。"""

    section_factories = [
        ("context_consistency", lambda: _inject_context_consistency_prompt(_ctx)),
        ("auto_advance", lambda: _inject_auto_advance_prompt(_ctx)),
        ("trpg_system", lambda: inject_trpg_system_prompt(_ctx)),
        ("game_state", lambda: inject_game_state_prompt(_ctx, character_manager, store)),
        ("system_expertise", lambda: inject_system_expertise_prompt(_ctx, character_manager)),
        ("session_history", lambda: inject_session_history_prompt(_ctx, battle_report_manager)),
        ("document_catalog", lambda: _inject_document_catalog_prompt(_ctx)),
        ("narrative_guidance", lambda: inject_narrative_guidance(_ctx, story_engine)),
        ("npc_state", lambda: _inject_npc_state_prompt(_ctx)),
        ("improvisation", lambda: inject_improvisation_guide(_ctx)),
        ("check_philosophy", lambda: inject_check_philosophy(_ctx)),
        ("dynamic_difficulty", lambda: inject_dynamic_difficulty(_ctx, story_engine)),
        ("npc_interaction", lambda: inject_npc_interaction_guide(_ctx)),
        ("check_index_schema", lambda: custom_rules.get_check_index_schema_prompt()),
        ("host_state", lambda: custom_rules.get_host_state_prompt(_ctx.chat_key)),
        ("custom_rules", lambda: custom_rules.get_custom_rules_prompt(_ctx.chat_key)),
        ("intelligent_rules", lambda: inject_intelligent_rule_system(_ctx, rule_modeler)),
        ("interaction_style", lambda: inject_interaction_style_prompt(_ctx)),
        ("final_guardrail", lambda: _inject_final_guardrail_prompt(_ctx)),
    ]

    sections = []
    for section_name, section_factory in section_factories:
        section = await _safe_prompt_section(section_name, section_factory)
        if section:
            sections.append(section)

    return "\n\n---\n\n".join(sections)


# ============ 文档上传沙盒方法 ============


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "upload_document", "上传并处理文档文件")
async def upload_document(
    _ctx: AgentCtx,
    file_path: str,
    doc_type: str = "module",
    custom_filename: Optional[str] = None,
) -> str:
    """
    处理用户上传的文档文件

    Args:
        file_path: AI提供的沙盒文件路径
        doc_type: 文档类型 (module/rule/story/background)
        custom_filename: 可选的自定义文件名

    Returns:
        处理结果信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"

    if doc_type not in ["module", "rule", "story", "background"]:
        return "❌ 文档类型必须是: module/rule/story/background"

    try:
        # 获取宿主机真实路径
        host_path = _ctx.fs.get_file(file_path)

        if not host_path.exists():
            return "❌ 指定的文件不存在"

        # 确定文件名
        if custom_filename:
            filename = custom_filename
        else:
            filename = host_path.stem  # 不包含扩展名的文件名

        # 读取文件内容并转换为文本
        with open(host_path, "rb") as f:
            file_content = f.read()

        # 根据文件扩展名提取文本
        original_filename = host_path.name
        try:
            text_content = vector_db.document_processor.extract_text_by_extension(original_filename, file_content)
        except ValueError as e:
            return f"❌ 文件处理失败: {str(e)}"

        if not text_content.strip():
            return "❌ 文件内容为空或无法提取文本"

        # 生成文档ID并存储到向量数据库
        document_id = str(uuid.uuid4())
        chat_key = _ctx.chat_key

        chunk_count = await vector_db.store_document(
            document_id=document_id,
            filename=filename,
            text_content=text_content,
            chat_key=chat_key,
            document_type=doc_type,
        )

        # 返回成功信息
        doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}[doc_type]
        result = f'✅ {doc_emoji} 文档 "{filename}" 上传成功！\n📊 已分割为 {chunk_count} 个片段\n📄 提取了 {len(text_content)} 个字符的文本内容'

        # 确保总是有返回值，不会为空
        if not result:
            result = f"✅ 文档上传完成（{filename}）"

        return result

    except Exception as e:
        error_msg = f"❌ 文档上传失败: {str(e)}"
        return error_msg


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "delete_document", "删除指定的文档")
async def delete_document(_ctx: AgentCtx, filename: str) -> str:
    """
    删除指定的文档

    Args:
        filename: 要删除的文档名称

    Returns:
        删除结果信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"

    try:
        chat_key = _ctx.chat_key

        # 查找该文档
        documents = await vector_db.list_documents(chat_key)
        target_doc = None

        for doc in documents:
            if doc["filename"] == filename:
                target_doc = doc
                break

        if not target_doc:
            return f'❌ 未找到名为 "{filename}" 的文档'

        # 删除文档
        success = await vector_db.delete_document(target_doc["document_id"], chat_key)

        if success:
            doc_emoji = {
                "module": "📘",
                "rule": "📜",
                "story": "📖",
                "background": "🌍",
            }.get(target_doc["document_type"], "📄")
            return f'✅ {doc_emoji} 文档 "{filename}" 已删除'
        else:
            return f'❌ 删除文档 "{filename}" 失败'

    except Exception as e:
        return f"❌ 删除文档失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "list_my_documents", "列出我的所有文档")
async def list_my_documents(_ctx: AgentCtx, doc_type: Optional[str] = None) -> str:
    """
    列出用户的所有文档

    Args:
        doc_type: 可选的文档类型过滤

    Returns:
        文档列表信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"

    try:
        chat_key = _ctx.chat_key

        documents = await vector_db.list_documents(chat_key, doc_type)

        if not documents:
            filter_text = f"类型为 {doc_type} 的" if doc_type else ""
            return f"📄 暂无{filter_text}已上传的文档"

        response = "📚 已上传的文档:\n"
        for i, doc in enumerate(documents, 1):
            doc_emoji = {
                "module": "📘",
                "rule": "📜",
                "story": "📖",
                "background": "🌍",
            }.get(doc["document_type"], "📄")
            response += f"{i}. {doc_emoji} {doc['filename']} ({doc['document_type']})\n"
            response += f"   预览: {doc['preview']}\n"

        # 确保总是有返回值，不会为空
        if not response:
            response = "📚 文档列表获取完成"

        return response

    except Exception as e:
        error_msg = f"❌ 获取文档列表失败: {str(e)}"
        return error_msg


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "search_documents", "搜索文档内容")
async def search_documents(_ctx: AgentCtx, query: str, doc_type: Optional[str] = None, limit: int = 5) -> str:
    """
    搜索文档内容

    Args:
        query: 搜索查询
        doc_type: 可选的文档类型过滤
        limit: 返回结果数量限制

    Returns:
        搜索结果信息
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"

    if not query.strip():
        return "❌ 请输入搜索关键词"

    try:
        chat_key = _ctx.chat_key

        results = await vector_db.search_documents(query=query, chat_key=chat_key, document_type=doc_type, limit=limit)

        if not results:
            return "🔍 未找到相关内容"

        response = f'🔍 搜索 "{query}" 的结果:\n'
        for i, result in enumerate(results, 1):
            response += f"{i}. {result['filename']} (相似度: {int(result['score'] * 100)}%)\n"
            response += f"   {result['text'][:100]}...\n\n"

        # 确保总是有返回值，不会为空
        if not response:
            response = "🔍 搜索完成，但未找到相关内容"

        return response

    except Exception as e:
        error_msg = f"❌ 搜索失败: {str(e)}"
        return error_msg


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "answer_document_question", "基于文档回答问题")
async def answer_document_question(_ctx: AgentCtx, question: str) -> str:
    """
    基于上传的文档回答问题

    Args:
        question: 用户的问题

    Returns:
        基于文档的回答
    """
    if not config.ENABLE_VECTOR_DB:
        return "❌ 文档功能未启用"

    if not question.strip():
        return "❌ 请输入你的问题"

    try:
        chat_key = _ctx.chat_key

        # 获取相关文档上下文
        context = await vector_db.get_document_context(question, chat_key)

        if not context:
            return "❌ 没有找到相关的文档内容来回答这个问题"

        # 这里可以集成AI来生成更好的回答
        # 目前先返回相关的文档片段
        return f"🤖 基于文档的相关内容:\n{context}\n\n💡 以上是从您上传的文档中找到的相关信息"

    except Exception as e:
        return f"❌ 问答失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_supported_file_types", "获取支持的文件类型")
async def get_supported_file_types(_ctx: AgentCtx) -> str:
    """
    获取支持的文件类型信息

    Returns:
        支持的文件类型列表
    """
    return """📄 支持的文件类型:
• TXT - 纯文本文件
• PDF - PDF文档 (需要PyPDF2)
• DOCX - Microsoft Word文档 (需要python-docx)

📚 文档类型:
• module - 📘 游戏模组、剧本内容
• rule - 📜 游戏规则、系统说明  
• story - 📖 背景故事、剧情内容
• background - 🌍 世界观、设定资料

💡 使用方法:
1. 直接上传文件到聊天窗口
2. 告诉我文件类型，我会自动处理
3. 处理完成后可以搜索和询问文档内容"""


# ============ 战报相关沙盒方法 ============


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "start_session_recording", "开始记录跑团会话")
async def start_session_recording(_ctx: AgentCtx, session_name: Optional[str] = None) -> str:
    """
    开始记录跑团会话，用于后续生成战报

    Args:
        session_name: 可选的会话名称

    Returns:
        开始记录的确认信息
    """
    try:
        await battle_report_manager.start_session(_ctx.chat_key, session_name)

        if session_name:
            return f"✅ 已开始记录跑团会话: {session_name}"
        else:
            return "✅ 已开始记录跑团会话，结束时将自动生成战报"
    except Exception as e:
        return f"❌ 开始记录失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "add_session_event", "记录跑团关键事件")
async def add_session_event(_ctx: AgentCtx, description: str, event_type: str = "general") -> str:
    """
    记录跑团中的关键事件

    Args:
        description: 事件描述
        event_type: 事件类型 (general/combat/story/discovery)

    Returns:
        记录结果
    """
    try:
        await battle_report_manager.add_key_event(_ctx.chat_key, description, event_type)
        return f"✅ 已记录关键事件: {description}"
    except Exception as e:
        return f"❌ 记录事件失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "generate_session_report", "生成跑团战报")
async def generate_session_report(_ctx: AgentCtx) -> str:
    """
    结束当前跑团并生成战报

    Returns:
        战报内容和Markdown文档
    """
    try:
        (
            text_report,
            markdown_report,
            session_name,
        ) = await battle_report_manager.generate_battle_report(_ctx.chat_key)

        if not text_report:
            return "❌ 没有正在进行的跑团会话"

        # 将Markdown文档保存到沙监文件系统
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"battle_report_{timestamp}.md"

        # 写入沙监文件系统
        sandbox_path = _ctx.fs.get_sandbox_path() / filename
        with open(sandbox_path, "w", encoding="utf-8") as f:
            f.write(markdown_report)

        # 返回文本战报和文档路径
        response = f"{text_report}\n\n📄 Markdown战报已生成: {filename}"

        return response

    except Exception as e:
        return f"❌ 生成战报失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_battle_report_markdown", "获取Markdown格式战报")
async def get_battle_report_markdown(_ctx: AgentCtx, timestamp: str) -> str:
    """
    获取之前生成的Markdown战报

    Args:
        timestamp: 战报的时间戳

    Returns:
        Markdown格式的战报内容
    """
    try:
        report_key = f"battle_report.{_ctx.chat_key}.{timestamp}"
        markdown_report = await store.get(store_key=report_key)

        if not markdown_report:
            return "❌ 未找到指定的战报"

        return markdown_report

    except Exception as e:
        return f"❌ 获取战报失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "request_player_roll", "创建玩家检定请求（AI不直接掷骰）")
async def request_player_roll(
    _ctx: AgentCtx, expression: str, reason: str = "场景检定", check_type: str = "general"
) -> str:
    expr = expression.strip()
    if not expr:
        return "❌ 请输入骰子表达式"

    pending = {
        "expression": expr,
        "reason": reason.strip() or "场景检定",
        "check_type": check_type.strip() or "general",
        "created_at": int(time.time()),
    }
    await _set_pending_roll(_ctx.chat_key, pending)
    return (
        "🎯 已创建检定请求\n"
        f"• 目的: {pending['reason']}\n"
        f"• 表达式: {pending['expression']}\n"
        "请玩家使用命令投骰（例如：r <表达式> 或 ra <技能>）"
    )


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_pending_roll", "查看当前待处理检定请求")
async def get_pending_roll(_ctx: AgentCtx) -> str:
    pending = await _get_pending_roll(_ctx.chat_key)
    if not pending:
        return "📭 当前没有待处理检定请求"
    return f"📌 当前待处理检定\n• 目的: {pending.get('reason', '检定')}\n• 表达式: {pending.get('expression', '')}"


# ============ 命令工具函数 ============


def _format_character_sheet(character: CharacterSheet) -> str:
    response = f"📋 角色卡: {character.name}\n"
    response += f"🎮 系统: {character.system}\n"

    if character.system == "CoC":
        attrs = ["STR", "CON", "DEX", "INT", "SAN", "HP"]
        attr_strs = [f"{attr}:{character.attributes[attr]}" for attr in attrs if attr in character.attributes]
        response += f"📊 属性: {' '.join(attr_strs)}\n"

        if character.skills:
            skill_list = list(character.skills.items())[:5]
            skill_strs = [f"{k}:{v}" for k, v in skill_list]
            response += f"🔧 技能: {' '.join(skill_strs)}..."

    return response


async def _record_dice_roll(
    context: CommandExecutionContext,
    expression: str,
    result: DiceResult,
    is_critical: bool,
) -> None:
    try:
        await battle_report_manager.ensure_session_started(context.chat_key)
        character = await character_manager.get_character(context.user_id, context.chat_key)
        char_name = character.name if character else "未知角色"
        await battle_report_manager.add_dice_roll(
            context.chat_key,
            context.user_id,
            char_name,
            expression,
            result.total,
            is_critical,
        )
    except Exception:
        pass


# ============ 骰子相关命令 ============


@plugin.mount_command(
    name="r",
    description="基础投骰",
    usage="r <表达式>",
    category="TRPG",
    tags=["trpg", "dice", "roll"],
)
async def handle_dice_roll(
    context: CommandExecutionContext,
    expression: Annotated[str, Arg("骰子表达式", positional=True, greedy=True)] = "",
) -> CommandResponse:
    expression = expression.strip()
    if not expression:
        return CmdCtl.failed("请输入骰子表达式，如: r 3d6+2")

    try:
        result = DiceRoller.roll_expression(expression)
    except ValueError as e:
        return CmdCtl.failed(f"❌ {str(e)}")

    response = f"🎲 {result.format_result()}"
    pending_tip = await _resolve_pending_roll(context.chat_key, expression)
    if pending_tip:
        response += pending_tip

    is_critical = False
    if result.is_critical_success():
        response += " ✨ 大成功!"
        is_critical = True
    elif result.is_critical_failure():
        response += " 💥 大失败!"
        is_critical = True

    await _record_dice_roll(context, expression, result, is_critical)
    return CmdCtl.success(response)


@plugin.mount_command(
    name="rh",
    description="隐藏掷骰",
    aliases=["rhide"],
    usage="rh <表达式>",
    category="TRPG",
    tags=["trpg", "dice", "hidden-roll"],
)
async def handle_hidden_roll(
    context: CommandExecutionContext,
    expression: Annotated[str, Arg("骰子表达式", positional=True, greedy=True)] = "",
) -> CommandResponse:
    expression = expression.strip()
    if not expression:
        return CmdCtl.failed("请输入骰子表达式，如: rh 3d6+2")

    try:
        result = DiceRoller.roll_expression(expression)
    except ValueError as e:
        return CmdCtl.failed(f"❌ {str(e)}")

    response = f"🎲 {result.format_result(show_details=False)}"
    pending_tip = await _resolve_pending_roll(context.chat_key, expression)
    if pending_tip:
        response += pending_tip
    return CmdCtl.success(response)


@plugin.mount_command(
    name="adv",
    description="D&D 优势掷骰",
    aliases=["advantage"],
    usage="adv [修正表达式]",
    category="TRPG",
    tags=["trpg", "dice", "advantage"],
)
async def handle_advantage_roll(
    context: CommandExecutionContext,
    expression: Annotated[str, Arg("修正表达式", positional=True, greedy=True)] = "",
) -> CommandResponse:
    expression = expression.strip() or "d20"
    try:
        result = DiceRoller.roll_advantage(expression)
    except ValueError as e:
        return CmdCtl.failed(f"❌ {str(e)}")

    response = f"🎲 优势掷骰: {result.format_result()}"
    pending_tip = await _resolve_pending_roll(context.chat_key, expression)
    if pending_tip:
        response += pending_tip
    return CmdCtl.success(response)


@plugin.mount_command(
    name="dis",
    description="D&D 劣势掷骰",
    aliases=["disadvantage"],
    usage="dis [修正表达式]",
    category="TRPG",
    tags=["trpg", "dice", "disadvantage"],
)
async def handle_disadvantage_roll(
    context: CommandExecutionContext,
    expression: Annotated[str, Arg("修正表达式", positional=True, greedy=True)] = "",
) -> CommandResponse:
    expression = expression.strip() or "d20"
    try:
        result = DiceRoller.roll_disadvantage(expression)
    except ValueError as e:
        return CmdCtl.failed(f"❌ {str(e)}")

    response = f"🎲 劣势掷骰: {result.format_result()}"
    pending_tip = await _resolve_pending_roll(context.chat_key, expression)
    if pending_tip:
        response += pending_tip
    return CmdCtl.success(response)


@plugin.mount_command(
    name="me",
    description="记录角色动作",
    usage="me <动作描述>",
    category="TRPG",
    tags=["trpg", "roleplay", "battle-report"],
)
async def handle_character_action(
    context: CommandExecutionContext,
    action: Annotated[str, Arg("角色动作", positional=True, greedy=True)] = "",
) -> CommandResponse:
    action = action.strip()
    if not action:
        return CmdCtl.failed("请描述你的角色动作，如: me 仔细观察房间")

    try:
        await battle_report_manager.ensure_session_started(context.chat_key)
        character = await character_manager.get_character(context.user_id, context.chat_key)
        char_name = character.name if character else "你"
        await battle_report_manager.add_player_action(context.chat_key, context.user_id, char_name, action)
        return CmdCtl.success(f"🎭 {char_name} {action}")
    except Exception:
        return CmdCtl.success(f"🎭 你 {action}")


@plugin.mount_command(
    name="nxt",
    description="请求 AI 自动推进当前跑团剧情",
    aliases=["next", "推进"],
    usage="nxt [推进要求]",
    category="TRPG",
    tags=["trpg", "story", "advance"],
)
async def handle_next_story(
    context: CommandExecutionContext,
    instruction: Annotated[str, Arg("可选的推进要求", positional=True, greedy=True)] = "",
) -> CommandResponse:
    from nekro_agent.services.message_service import message_service

    instruction = instruction.strip()
    prompt = (
        "玩家请求继续推进当前 TRPG 跑团剧情。\n"
        "请基于当前频道已记录的角色卡、剧情状态、线索、NPC、文档资料、待处理检定和战报历史继续主持。\n"
        "如果当前存在待处理检定，不要直接叙述最终成败，应提醒玩家先完成对应投骰。\n"
        "如果没有待处理检定，请推进一个自然的下一步场景、NPC反应、环境变化或玩家可选择的行动机会。\n"
        "不要编造骰点；需要随机性时调用 request_player_roll 创建玩家检定请求。"
    )
    if instruction:
        prompt += f"\n玩家补充推进要求: {instruction}"

    await _set_auto_advance_request(context.chat_key, instruction)
    await message_service.push_system_message(chat_key=context.chat_key, agent_messages=prompt, trigger_agent=True)
    return CmdCtl.success("✅ 已请求 AI 继续推进当前跑团剧情")


@plugin.mount_command(
    name="ra",
    description="角色技能检定",
    usage="ra <技能>",
    category="TRPG",
    tags=["trpg", "dice", "skill-check"],
)
async def handle_skill_check(
    context: CommandExecutionContext,
    skill_input: Annotated[str, Arg("技能名称", positional=True, greedy=True)] = "",
) -> CommandResponse:
    skill_input = skill_input.strip()
    if not skill_input:
        return CmdCtl.failed("请输入技能名称，如: ra 侦察")

    try:
        await battle_report_manager.ensure_session_started(context.chat_key)
        character = await character_manager.get_character(context.user_id, context.chat_key)
        skill_name = character_manager.find_skill_by_alias(character, skill_input) or skill_input
        skill_value = character.skills.get(skill_name, 50)

        if character.system == "CoC":
            result = DiceRoller.roll_coc_check(skill_value)
            response = (
                f"🎲 {character.name} 进行 {skill_name} 检定:\n"
                f"🎯 掷出 {result['roll']} (目标值: {skill_value})\n"
                f"✨ 结果: {result['level']}"
            )
            pending_tip = await _resolve_pending_roll(context.chat_key, f"ra {skill_name}")
            if pending_tip:
                response += pending_tip
            try:
                await battle_report_manager.add_skill_check(
                    context.chat_key,
                    context.user_id,
                    character.name,
                    skill_name,
                    skill_value,
                    result["roll"],
                    result["level"],
                )
            except Exception:
                pass
            return CmdCtl.success(response)

        result = DiceRoller.roll_expression("d20")
        response = f"🎲 {character.name} 进行 {skill_name} 检定: {result.format_result()}"
        pending_tip = await _resolve_pending_roll(context.chat_key, "d20")
        if pending_tip:
            response += pending_tip
        return CmdCtl.success(response)
    except Exception as e:
        return CmdCtl.failed(f"❌ 检定失败: {str(e)}")


# ============ 角色卡管理命令 ============


@plugin.mount_command(
    name="st",
    description="角色卡管理",
    usage="st [show|new <名称>|temp <模板>|init]",
    category="TRPG",
    tags=["trpg", "character"],
)
async def handle_character_sheet(
    context: CommandExecutionContext,
    command: Annotated[str, Arg("角色卡命令", positional=True, greedy=True)] = "",
) -> CommandResponse:
    command = command.strip()

    if not command or command == "show":
        try:
            character = await character_manager.get_character(context.user_id, context.chat_key)
            return CmdCtl.success(_format_character_sheet(character))
        except Exception as e:
            return CmdCtl.failed(f"❌ 获取角色卡失败: {str(e)}")

    if command.startswith("new "):
        char_name = command[4:].strip()
        if not char_name:
            return CmdCtl.failed("请指定角色名称")

        char_name = re.sub(r"[<>\[\]{}]", "", char_name).strip()
        if not char_name:
            return CmdCtl.failed("角色名称不能为空或只包含特殊字符")

        try:
            character = CharacterSheet(name=char_name)
            await character_manager.save_character(context.user_id, context.chat_key, character)
            return CmdCtl.success(f"✅ 已创建角色: {char_name}")
        except Exception as e:
            return CmdCtl.failed(f"❌ 保存角色失败: {str(e)}")

    if command.startswith("temp "):
        template_name = command[5:].strip().lower()
        if template_name not in ["coc7", "dnd5e"]:
            return CmdCtl.failed("❌ 支持的模板: coc7, dnd5e")

        character = await character_manager.get_character(context.user_id, context.chat_key)
        character.system = "CoC" if template_name == "coc7" else "DnD5e"
        await character_manager.save_character(context.user_id, context.chat_key, character)
        return CmdCtl.success(f"✅ 已切换到 {template_name} 模板")

    if command == "init":
        character = await character_manager.get_character(context.user_id, context.chat_key)
        template_name = "coc7" if character.system == "CoC" else "dnd5e"
        new_character = character_manager.generate_character(template_name, character.name)
        await character_manager.save_character(context.user_id, context.chat_key, new_character)
        return CmdCtl.success(f"✅ 已自动生成角色属性: {new_character.name}")

    return CmdCtl.failed("用法: st [show/new <名称>/temp <模板>/init]")


# ============ 文档管理命令 ============


@plugin.mount_command(
    name="doc",
    description="文档系统帮助、列表和搜索",
    aliases=["文档", "模组"],
    usage="doc [list|search <关键词>]",
    category="TRPG",
    tags=["trpg", "document"],
)
async def handle_document_help(
    context: CommandExecutionContext,
    command: Annotated[str, Arg("文档命令", positional=True, greedy=True)] = "",
) -> CommandResponse:
    if not config.ENABLE_VECTOR_DB:
        return CmdCtl.failed("❌ 文档功能未启用")

    command = command.strip()

    if command == "list":
        try:
            documents = await vector_db.list_documents(context.chat_key)
        except Exception as e:
            return CmdCtl.failed(f"❌ 获取文档列表失败: {str(e)}")

        if not documents:
            return CmdCtl.success("📄 暂无已上传的文档")

        response = "📚 已上传的文档:\n"
        for i, doc in enumerate(documents, 1):
            doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}.get(
                doc["document_type"], "📄"
            )
            response += f"{i}. {doc_emoji} {doc['filename']} ({doc['document_type']})\n"
        return CmdCtl.success(response)

    if command.startswith("search "):
        query = command[7:].strip()
        if not query:
            return CmdCtl.failed("请输入搜索关键词")

        try:
            results = await vector_db.search_documents(
                query=query, chat_key=context.chat_key, limit=config.MAX_SEARCH_RESULTS
            )
        except Exception as e:
            return CmdCtl.failed(f"❌ 搜索失败: {str(e)}")

        if not results:
            return CmdCtl.success("🔍 未找到相关内容")

        response = f'🔍 搜索 "{query}" 的结果:\n'
        for i, result in enumerate(results, 1):
            response += f"{i}. {result['filename']} (相似度: {int(result['score'] * 100)}%)\n"
            response += f"   {result['text'][:100]}...\n"
        return CmdCtl.success(response)

    help_text = """📚 文档系统使用说明:

📤 上传文档:
🔹 方式一：直接上传文件
• 将PDF、DOCX、TXT文件直接拖拽到聊天窗口
• 告诉我文档类型(module/rule/story/background)，我会自动处理

🔹 方式二：文本输入
• doc_text <类型> <文档名> <内容>
• 类型: module(模组) / rule(规则) / story(故事) / background(背景)

🔍 搜索管理:
• doc search <关键词> - 搜索文档内容
• doc list - 列出所有文档
• ask <问题> - 智能问答

💡 使用示例:
📁 文件上传: "帮我处理这个模组PDF文件"
📝 文本输入: doc_text module 深海古城 [模组内容...]
🔍 搜索: doc search 深海古城的NPC
❓ 问答: ask 这个模组的主要剧情是什么

📄 支持格式: TXT, PDF, DOCX"""
    return CmdCtl.success(help_text)


@plugin.mount_command(
    name="doc_text",
    description="上传文本文档到当前频道文档库",
    aliases=["文档文本", "text"],
    usage="doc_text <类型> <文档名> <内容>",
    category="TRPG",
    tags=["trpg", "document", "upload"],
)
async def handle_upload_text_document(
    context: CommandExecutionContext,
    content: Annotated[str, Arg("类型 文档名 内容", positional=True, greedy=True)] = "",
) -> CommandResponse:
    if not config.ENABLE_VECTOR_DB:
        return CmdCtl.failed("❌ 文档功能未启用")

    parts = content.strip().split(" ", 2)
    if len(parts) < 3:
        return CmdCtl.failed("用法: doc_text <类型> <文档名> <内容>\n类型: module/rule/story/background")

    doc_type = parts[0].lower()
    filename = parts[1]
    text_content = parts[2]

    if doc_type not in ["module", "rule", "story", "background"]:
        return CmdCtl.failed("❌ 文档类型必须是: module/rule/story/background")

    try:
        document_id = str(uuid.uuid4())
        chunk_count = await vector_db.store_document(
            document_id=document_id,
            filename=filename,
            text_content=text_content,
            chat_key=context.chat_key,
            document_type=doc_type,
        )
    except Exception as e:
        return CmdCtl.failed(f"❌ 上传失败: {str(e)}")

    doc_emoji = {"module": "📘", "rule": "📜", "story": "📖", "background": "🌍"}[doc_type]
    return CmdCtl.success(f'✅ {doc_emoji} 文档 "{filename}" 上传成功！\n📊 已分割为 {chunk_count} 个片段')


@plugin.mount_command(
    name="ask",
    description="基于上传文档问答",
    aliases=["问答", "询问", "qa"],
    usage="ask <问题>",
    category="TRPG",
    tags=["trpg", "document", "qa"],
)
async def handle_document_qa(
    context: CommandExecutionContext,
    question: Annotated[str, Arg("问题", positional=True, greedy=True)] = "",
) -> CommandResponse:
    if not config.ENABLE_VECTOR_DB:
        return CmdCtl.failed("❌ 文档功能未启用")

    question = question.strip()
    if not question:
        return CmdCtl.failed("请输入你的问题")

    try:
        answer = await vector_db.answer_question(question=question, chat_key=context.chat_key)
        return CmdCtl.success(f"🤖 AI回答:\n{answer}")
    except Exception as e:
        return CmdCtl.failed(f"❌ 问答失败: {str(e)}")


# ============ AI角色构建沙盒方法 ============


@plugin.mount_sandbox_method(
    SandboxMethodType.TOOL,
    "ai_create_character_from_file",
    "AI从上传的文件智能创建角色",
)
async def ai_create_character_from_file(_ctx: AgentCtx, file_path: str, system: Optional[str] = None) -> str:
    """
    从上传的文件智能创建TRPG角色卡

    Args:
        file_path: 上传的文件路径（TXT/PDF/DOCX）
        system: 可选的游戏系统指定 ("coc7"/"dnd5e"/None自动识别)

    Returns:
        角色预览和临时ID
    """
    try:
        # 获取文件内容
        host_path = _ctx.fs.get_file(file_path)

        if not host_path.exists():
            return "❌ 指定的文件不存在"

        # 读取文件内容
        with open(host_path, "rb") as f:
            file_content = f.read()

        # 提取文本
        try:
            document_text = DocumentProcessor.extract_text_by_extension(host_path.name, file_content)
        except ValueError as e:
            return f"❌ 文件处理失败: {str(e)}"

        if not document_text.strip():
            return "❌ 文件内容为空或无法提取文本"

        # 构建角色卡
        character, metadata = await ai_character_builder.build_character_sheet(document_text, system)

        # 存储临时角色
        temp_id = ai_character_builder.store_temp_character(character, metadata)

        # 生成预览
        preview = ai_character_builder.format_preview(character, metadata)

        # 返回预览和临时ID
        response = f"{preview}\n\n🔑 临时ID: `{temp_id}`\n请使用 `confirm_character_creation` 确认创建此角色"

        return response

    except Exception as e:
        return f"❌ 角色创建失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "confirm_character_creation", "确认并保存AI创建的角色")
async def confirm_character_creation(_ctx: AgentCtx, temp_id: str, modifications: Optional[dict] = None) -> str:
    """
    确认并保存AI创建的角色卡

    Args:
        temp_id: 临时角色ID（来自ai_create_character_from_file）
        modifications: 可选的修改信息 {属性修改等}

    Returns:
        创建成功的确认信息
    """
    try:
        # 获取临时角色
        result = ai_character_builder.get_temp_character(temp_id)
        if result is None:
            return f"❌ 临时角色已过期或不存在 (ID: {temp_id})"

        character, metadata = result

        # 应用修改（如果有）
        if modifications:
            try:
                # 简单的修改支持：可以修改属性、技能等
                if "attributes" in modifications:
                    for attr_name, attr_value in modifications["attributes"].items():
                        if attr_name in character.attributes:
                            character.attributes[attr_name] = int(attr_value)

                if "skills" in modifications:
                    for skill_name, skill_value in modifications["skills"].items():
                        if skill_name in character.skills:
                            character.skills[skill_name] = int(skill_value)

                if "name" in modifications:
                    character.name = modifications["name"]

                if "background" in modifications:
                    character.background = modifications["background"]
            except Exception as e:
                return f"⚠️ 部分修改失败: {str(e)}，但角色将使用原始配置保存"

        # 保存角色
        user_id = str(_ctx.user_id)
        chat_key = _ctx.chat_key

        await character_manager.save_character(user_id, chat_key, character)

        # 删除临时角色
        ai_character_builder.remove_temp_character(temp_id)

        # 返回成功信息
        response = f"""✅ 角色创建成功！

📋 角色卡已保存
• 姓名: {character.name}
• 系统: {character.system}
• 职业: {character.occupation or "未设定"}
• 年龄: {character.age}岁

💡 接下来可以：
• 使用 'st' 查看完整角色卡
• 使用 'ra <技能>' 进行技能检定
• 开始跑团冒险！"""

        return response

    except Exception as e:
        return f"❌ 保存角色失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "list_character_creation_guide", "获取AI角色创建指南")
async def list_character_creation_guide(_ctx: AgentCtx) -> str:
    """获取AI智能创建角色的使用说明"""
    guide = """📚 AI角色创建指南

## 功能说明
通过上传包含角色信息的文档，AI会智能提取信息并创建TRPG角色卡。

## 支持的文件格式
• 📄 TXT - 纯文本文件（推荐）
• 📕 PDF - PDF文档（需要PyPDF2）
• 📗 DOCX - Word文档（需要python-docx）

## 文件内容要求
角色文件应该包含以下信息（不需要全部有）：
• **基础信息**: 姓名、年龄、性别、职业、身份
• **属性数据**: 力量、敏捷、体质等数值（COC7/DND5E）
• **技能信息**: 擅长的技能及其数值
• **背景故事**: 角色的背景、经历、性格特征

## 使用流程
1. 📤 上传角色信息文件
2. 🤖 AI自动分析和提取信息
3. 👁️ 查看生成的角色卡预览
4. ✅ 确认无误后创建角色卡

## 示例
```
AI会自动识别文档中的信息，比如：
- "STR 50" 或 "力量 16" → 识别为属性
- "侦查 75" 或 "侦察技能不错" → 识别为技能
- "私家侦探" → 识别为职业
- "28岁的女性调查员..." → 识别为年龄、性别和背景
```

## 智能补全
如果文件中缺少某些信息，AI会根据以下规则自动补全：
• 缺失属性 → 使用系统默认值（COC7=50, DND5E=10）
• 缺失技能 → 根据职业推荐合理的技能
• 缺失背景 → 使用空值，可后续编辑
• 缺失系统 → AI自动识别（COC7/DND5E）

## 支持的游戏系统
• ✨ COC7 (克苏鲁的呼唤第7版)
• ⚔️ DND5E (龙与地下城第5版)
• 🤖 自动识别（AI根据内容判断）

## 常见问题
**Q: 文件中信息不完整怎么办？**
A: AI会自动补全缺失信息，创建后可以使用 'st' 命令查看和编辑

**Q: 能创建多个角色吗？**
A: 可以，每个用户可以创建多个角色并管理

**Q: 创建后能修改吗？**
A: 可以，确认前可以指定修改，或创建后使用其他命令编辑

**Q: 缺失的信息会怎样？**
A: AI会根据职业和其他信息进行合理推断和补全"""

    return guide


# ============ 其他实用命令 ============


@plugin.mount_command(
    name="jrrp",
    description="今日人品",
    usage="jrrp",
    category="TRPG",
    tags=["trpg", "luck"],
)
async def handle_daily_luck(context: CommandExecutionContext) -> CommandResponse:
    """今日人品"""
    try:
        luck_value = await character_manager.get_daily_luck(context.user_id)

        if luck_value >= 90:
            level = "超级欧皇"
        elif luck_value >= 70:
            level = "欧洲人"
        elif luck_value >= 30:
            level = "平民"
        else:
            level = "非洲人"

        return CmdCtl.success(f"🍀 今日人品值: {luck_value} ({level})")
    except Exception as e:
        return CmdCtl.failed(f"❌ 获取人品失败: {str(e)}")


@plugin.mount_command(
    name="trpg_help",
    description="TRPG 骰子系统帮助",
    aliases=["trpg"],
    usage="trpg_help",
    category="TRPG",
    tags=["trpg", "help"],
)
async def handle_help(context: CommandExecutionContext) -> CommandResponse:
    """帮助信息"""
    help_text = """🎲 TRPG骰子系统 v1.0.0

🎯 基础指令:
• r <表达式> - 投骰 (如: r 3d6+2)
• ra <技能> - 技能检定
• me <动作> - 角色动作
• st - 角色卡管理

📚 文档系统:
• 直接上传文件 - 支持PDF/DOCX/TXT文件自动处理
• doc - 查看文档帮助
• ask <问题> - 基于上传文档的智能问答

📄 战报系统:
• session start [名称] - 开始记录跑团
• session end - 结束并生成战报
• session event <描述> - 记录关键事件

🍀 实用功能:
• jrrp - 今日人品
• help - 显示帮助

💡 新特性: 直接上传模组PDF文件，系统会自动解析并支持智能问答！
详细说明请使用各命令的帮助功能！"""

    return CmdCtl.success(help_text)


# ============ 战报管理命令 ============


@plugin.mount_command(
    name="session",
    description="跑团会话和战报管理",
    aliases=["跑团", "会话"],
    usage="session [start [名称]|end|event <描述>]",
    category="TRPG",
    tags=["trpg", "session", "battle-report"],
)
async def handle_session(
    context: CommandExecutionContext,
    command: Annotated[str, Arg("会话命令", positional=True, greedy=True)] = "",
) -> CommandResponse:
    """跑团会话管理"""
    command = command.strip()
    chat_key = context.chat_key

    if command.startswith("start"):
        # 开始记录
        parts = command.split(maxsplit=1)
        session_name = parts[1] if len(parts) > 1 else None

        try:
            await battle_report_manager.start_session(chat_key, session_name)
            if session_name:
                return CmdCtl.success(
                    f"✅ 已开始记录跑团会话: {session_name}\n\n📝 所有投骰、检定和行动将自动记录\n📄 结束时使用 'session end' 生成战报"
                )
            else:
                return CmdCtl.success(
                    "✅ 已开始记录跑团会话\n\n📝 所有投骰、检定和行动将自动记录\n📄 结束时使用 'session end' 生成战报"
                )
        except Exception as e:
            return CmdCtl.failed(f"❌ 开始记录失败: {str(e)}")

    elif command == "end":
        # 结束并生成战报
        try:
            (
                text_report,
                markdown_report,
                session_name,
            ) = await battle_report_manager.generate_battle_report(chat_key)

            if not text_report:
                return CmdCtl.failed("❌ 没有正在进行的跑团会话")

            # 保存Markdown文档到存储
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"battle_report_{timestamp}.md"

            # 将Markdown内容保存到存储
            report_key = f"battle_report.{chat_key}.{timestamp}"
            await store.set(store_key=report_key, value=markdown_report)

            return CmdCtl.success(f"{text_report}\n\n📄 Markdown战报已生成: {filename}\n请告诉AI获取Markdown战报文档")

        except Exception as e:
            return CmdCtl.failed(f"❌ 生成战报失败: {str(e)}")

    elif command.startswith("event"):
        # 记录关键事件
        parts = command.split(maxsplit=1)
        if len(parts) < 2:
            return CmdCtl.failed("请输入事件描述，如: session event 发现了神秘的地下入口")

        description = parts[1]
        try:
            await battle_report_manager.add_key_event(chat_key, description)
            return CmdCtl.success(f"✅ 已记录关键事件: {description}")
        except Exception as e:
            return CmdCtl.failed(f"❌ 记录事件失败: {str(e)}")

    else:
        # 显示帮助
        help_text = """📄 跑团战报系统

🎯 使用方法:
• session start [名称] - 开始记录跑团会话
• session end - 结束并生成战报
• session event <描述> - 记录关键事件

📊 自动记录项:
• 🎲 所有投骰结果
• 🎯 技能检定详情
• 🎭 角色动作 (me命令)

🏆 战报内容:
• 每位PC的详细评分（5星级别）
• 游戏时长和统计数据
• 关键事件回顾
• 精彩时刻（大成功/大失败）

📄 输出格式:
• 聊天窗口显示文本版战报
• 自动生成Markdown文档

💡 示例:
session start 深海古城探险  # 开始记录
session event 发现了神秘的地下入口  # 记录关键事件
session end  # 生成战报"""

        return CmdCtl.success(help_text)


# ============ 自定义规则沙盒方法 ============


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "define_rule", "定义自定义规则")
async def define_rule(_ctx: AgentCtx, rule_name: str, description: str, examples: str = "") -> str:
    try:
        await custom_rules.define_custom_rule(_ctx.chat_key, rule_name, description, examples)
        return f"✅ 规则已定义: {rule_name}"
    except Exception as e:
        return f"❌ 定义规则失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "define_attribute", "定义自定义属性")
async def define_attribute(_ctx: AgentCtx, attr_name: str, attr_type: str, default_value: str, description: str) -> str:
    try:
        await custom_rules.define_custom_attribute(_ctx.chat_key, attr_name, attr_type, default_value, description)
        return f"✅ 属性已定义: {attr_name} ({attr_type})"
    except Exception as e:
        return f"❌ 定义属性失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "upsert_check_metric", "新增或更新结构化判定指标 JSON")
async def upsert_check_metric(_ctx: AgentCtx, metric_id: str, metric_json: str) -> str:
    """新增或更新 TRPG 判定指标。

    Args:
        metric_id: 判定指标唯一 ID，例如 coc_spot_hidden
        metric_json: JSON 字符串，字段参考提示词中的 TRPG判定索引记录格式
    """
    try:
        metric = json.loads(metric_json)
        if not isinstance(metric, dict):
            return "❌ metric_json 必须是 JSON 对象"
        normalized = await custom_rules.upsert_check_metric(_ctx.chat_key, metric_id, metric)
        return "✅ 判定指标已记录:\n```json\n" + json.dumps(normalized, ensure_ascii=False, indent=2) + "\n```"
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析失败: {str(e)}"
    except Exception as e:
        return f"❌ 记录判定指标失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_check_index", "获取当前频道结构化判定索引 JSON")
async def get_check_index(_ctx: AgentCtx) -> str:
    try:
        check_index = await custom_rules.get_check_index(_ctx.chat_key)
        if not check_index:
            return "📭 当前频道还没有结构化判定索引"
        return "```json\n" + json.dumps(check_index, ensure_ascii=False, indent=2) + "\n```"
    except Exception as e:
        return f"❌ 获取判定索引失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "remove_check_metric", "删除结构化判定指标")
async def remove_check_metric(_ctx: AgentCtx, metric_id: str) -> str:
    try:
        removed = await custom_rules.remove_check_metric(_ctx.chat_key, metric_id)
        if not removed:
            return f"❌ 未找到判定指标: {metric_id}"
        return f"✅ 已删除判定指标: {metric_id}"
    except Exception as e:
        return f"❌ 删除判定指标失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "upsert_map_scene", "新增或更新普通地图/探索场景 JSON")
async def upsert_map_scene(_ctx: AgentCtx, scene_id: str, scene_json: str) -> str:
    try:
        scene = json.loads(scene_json)
        if not isinstance(scene, dict):
            return "❌ scene_json 必须是 JSON 对象"
        normalized = await custom_rules.upsert_map_scene(_ctx.chat_key, scene_id, scene)
        await story_engine.set_scene(_ctx.chat_key, normalized["name"], SceneMood.MYSTERIOUS)
        return (
            "✅ 场景已记录并设为当前场景:\n```json\n" + json.dumps(normalized, ensure_ascii=False, indent=2) + "\n```"
        )
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析失败: {str(e)}"
    except Exception as e:
        return f"❌ 记录场景失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "set_active_scene", "切换当前普通地图/探索场景")
async def set_active_scene(_ctx: AgentCtx, scene_id: str) -> str:
    try:
        ok = await custom_rules.set_active_scene(_ctx.chat_key, scene_id)
        if not ok:
            return f"❌ 未找到场景: {scene_id}"
        await story_engine.set_scene(_ctx.chat_key, scene_id, SceneMood.MYSTERIOUS)
        return f"✅ 当前场景已切换为: {scene_id}"
    except Exception as e:
        return f"❌ 切换场景失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "get_host_state", "获取当前主持状态 JSON")
async def get_host_state(_ctx: AgentCtx) -> str:
    try:
        host_state = await custom_rules.get_host_state(_ctx.chat_key)
        return "```json\n" + json.dumps(host_state, ensure_ascii=False, indent=2) + "\n```"
    except Exception as e:
        return f"❌ 获取主持状态失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "start_combat", "开启战斗并按先攻/速度排序")
async def start_combat(_ctx: AgentCtx, combat_json: str) -> str:
    try:
        combat = json.loads(combat_json)
        if not isinstance(combat, dict):
            return "❌ combat_json 必须是 JSON 对象"
        combat_state = await custom_rules.start_combat(_ctx.chat_key, combat)
        return (
            "⚔️ 战斗已开启，回合顺序已按 initiative/speed 排序:\n```json\n"
            + json.dumps(combat_state, ensure_ascii=False, indent=2)
            + "\n```"
        )
    except json.JSONDecodeError as e:
        return f"❌ JSON 解析失败: {str(e)}"
    except Exception as e:
        return f"❌ 开启战斗失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "advance_combat_turn", "推进到下一个战斗回合")
async def advance_combat_turn(_ctx: AgentCtx) -> str:
    try:
        combat = await custom_rules.advance_combat_turn(_ctx.chat_key)
        participants = combat.get("participants") or []
        current = participants[int(combat.get("turn_index") or 0)]
        return (
            f"✅ 已推进到第 {combat.get('round', 1)} 轮，当前行动者: {current.get('name')} ({current.get('id')})\n"
            "```json\n" + json.dumps(combat, ensure_ascii=False, indent=2) + "\n```"
        )
    except Exception as e:
        return f"❌ 推进战斗回合失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "end_combat", "结束当前战斗并回到普通场景")
async def end_combat(_ctx: AgentCtx) -> str:
    try:
        combat = await custom_rules.end_combat(_ctx.chat_key)
        return (
            "✅ 战斗已结束，回到普通探索场景。\n```json\n" + json.dumps(combat, ensure_ascii=False, indent=2) + "\n```"
        )
    except Exception as e:
        return f"❌ 结束战斗失败: {str(e)}"


# ============ 智能剧情管理沙盒方法 ============


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "set_scene", "设置当前场景和氛围")
async def set_scene(_ctx: AgentCtx, scene_name: str, mood: str = "mysterious") -> str:
    try:
        mood_map = {
            "peaceful": SceneMood.PEACEFUL,
            "mysterious": SceneMood.MYSTERIOUS,
            "horror": SceneMood.HORROR,
            "epic": SceneMood.EPIC,
            "melancholy": SceneMood.MELANCHOLY,
        }
        scene_mood = mood_map.get(mood.lower(), SceneMood.MYSTERIOUS)
        await story_engine.set_scene(_ctx.chat_key, scene_name, scene_mood)
        return f"✅ 场景已设置: {scene_name} ({scene_mood.value})"
    except Exception as e:
        return f"❌ 设置场景失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "set_tension", "调整剧情紧张度")
async def set_tension(_ctx: AgentCtx, level: int) -> str:
    try:
        tension_levels = {
            1: TensionLevel.CALM,
            3: TensionLevel.CURIOUS,
            5: TensionLevel.TENSE,
            7: TensionLevel.DANGEROUS,
            9: TensionLevel.CRITICAL,
        }
        tension = tension_levels.get(level, TensionLevel.TENSE)
        await story_engine.set_tension(_ctx.chat_key, tension)
        return f"✅ 紧张度已调整至: {level}"
    except Exception as e:
        return f"❌ 调整紧张度失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "add_clue", "添加线索到剧情追踪")
async def add_clue(_ctx: AgentCtx, clue: str) -> str:
    try:
        await story_engine.add_clue(_ctx.chat_key, clue)
        return f"✅ 线索已记录: {clue}"
    except Exception as e:
        return f"❌ 记录线索失败: {str(e)}"


# ============ NPC 管理沙盒方法 ============


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "create_npc", "创建 NPC")
async def create_npc(
    _ctx: AgentCtx,
    npc_id: str,
    name: str,
    personality: str,
    background: str,
    secrets: str = "",
) -> str:
    try:
        secret_list = [s.strip() for s in secrets.split("|") if s.strip()] if secrets else []
        await npc_manager.create_npc(_ctx.chat_key, npc_id, name, personality, background, secret_list)
        return f"✅ NPC 已创建: {name}\n性格: {personality}\n背景: {background[:50]}..."
    except Exception as e:
        return f"❌ 创建 NPC 失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "npc_remember", "让 NPC 记住事件")
async def npc_remember(_ctx: AgentCtx, npc_id: str, memory: str) -> str:
    try:
        await npc_manager.add_memory(_ctx.chat_key, npc_id, memory)
        return f"✅ {npc_id} 已记住: {memory}"
    except Exception as e:
        return f"❌ 记录失败: {str(e)}"


@plugin.mount_sandbox_method(SandboxMethodType.TOOL, "update_npc_relationship", "更新 NPC 关系")
async def update_npc_relationship(_ctx: AgentCtx, npc_id: str, target: str, change: int) -> str:
    try:
        await npc_manager.update_relationship(_ctx.chat_key, npc_id, target, change)
        direction = "提升" if change > 0 else "下降"
        return f"✅ {npc_id} 对 {target} 的好感度{direction} {abs(change)}"
    except Exception as e:
        return f"❌ 更新关系失败: {str(e)}"


# ============ 清理方法 ============


@plugin.mount_cleanup_method()
async def clean_up():
    pass
