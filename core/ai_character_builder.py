"""
TRPG AI角色构建器 - 从文档智能创建角色卡

功能：
- 从上传的文档自动提取角色信息
- 自动识别游戏系统（COC7/DND5E）
- 智能补全缺失的属性和技能
- 生成完整角色卡并预览
"""

import json
import time
import uuid
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from .character_manager import CharacterSheet, CharacterManager, CharacterTemplate


class AICharacterBuilder:
    """
    AI角色构建器 - 从文档智能创建TRPG角色

    功能流程：
    1. 接收文档文本
    2. 调用LLM分析并提取角色信息
    3. 自动识别游戏系统
    4. 补全缺失信息
    5. 生成完整角色卡
    """

    def __init__(self, character_manager: CharacterManager):
        """
        初始化AI角色构建器

        Args:
            character_manager: CharacterManager实例，用于访问模板和保存角色
        """
        self.character_manager = character_manager
        self.templates = character_manager.templates

        # 临时角色存储 {temp_id: {character, created_time}}
        self.temp_characters: Dict[str, Dict] = {}

        # COC7标准属性和技能
        self.coc7_attributes = {
            "STR": 50, "CON": 50, "SIZ": 50, "DEX": 50,
            "APP": 50, "INT": 50, "POW": 50, "EDU": 50, "LUC": 50
        }

        self.coc7_skills = {
            "会计": 5, "人类学": 1, "估价": 5, "考古学": 1, "取悦": 15,
            "攀爬": 20, "计算机使用": 5, "信用": 0, "克苏鲁神话": 0,
            "乔装": 5, "闪避": 25, "汽车驾驶": 20, "电气维修": 10,
            "电子学": 1, "话术": 5, "急救": 30, "历史": 5,
            "恐吓": 15, "跳跃": 20, "母语": 50, "法律": 5,
            "图书馆": 20, "聆听": 20, "锁匠": 1, "机械维修": 10,
            "医学": 1, "博物": 10, "导航": 10, "神秘学": 5,
            "操作重型机械": 1, "说服": 10, "精神分析": 1, "心理学": 10,
            "骑乘": 5, "妙手": 10, "侦查": 25, "潜行": 20,
            "游泳": 20, "投掷": 20, "追踪": 10, "驯兽": 5,
            "潜水": 1, "爆破": 1, "读唇": 1, "催眠": 1,
            "炮术": 1, "手枪": 20, "步霰": 25, "斗殴": 20
        }

        # DND5E属性
        self.dnd5e_attributes = {
            "力量": 10, "敏捷": 10, "体质": 10,
            "智力": 10, "感知": 10, "魅力": 10
        }

    def detect_game_system(self, document_text: str, explicit_system: Optional[str] = None) -> str:
        """
        检测文档中的游戏系统

        Args:
            document_text: 文档内容
            explicit_system: 显式指定的系统 ("coc7" 或 "dnd5e")

        Returns:
            识别到的系统标识 ("CoC" 或 "DnD5e")
        """
        # 如果显式指定了系统
        if explicit_system:
            if explicit_system.lower() in ["coc7", "coc", "克苏鲁"]:
                return "CoC"
            elif explicit_system.lower() in ["dnd5e", "dnd5", "龙与地下城"]:
                return "DnD5e"

        # 根据文档内容推断
        text_lower = document_text.lower()

        # COC7 关键词
        coc_keywords = ["san", "理智", "克苏鲁", "coc", "调查员", "秘密战争", "1d100"]
        coc_score = sum(1 for keyword in coc_keywords if keyword in text_lower)

        # DND5E 关键词
        dnd_keywords = ["力量", "敏捷", "体质", "智力", "感知", "魅力", "dnd", "d20", "等级", "职业"]
        dnd_score = sum(1 for keyword in dnd_keywords if keyword in text_lower)

        # 返回得分更高的系统，默认COC
        if dnd_score > coc_score and dnd_score > 0:
            return "DnD5e"
        return "CoC"

    async def extract_character_info(self, document_text: str) -> Dict[str, Any]:
        """
        使用AI从文档中提取角色信息

        Args:
            document_text: 文档内容文本

        Returns:
            提取的角色信息字典
        """
        from nekro_agent.services.agent.openai import gen_openai_chat_response

        # 构建提示词
        extraction_prompt = f"""你是专业的TRPG角色卡生成助手，精通COC7和DND5E规则。

## 任务
从以下文档中提取角色信息，输出结构化JSON。

## 提取规则
1. 识别游戏系统（COC7/DND5E）
2. 提取明确的数值（属性、技能）
3. 对缺失信息进行合理推断
4. 保留原始背景故事
5. 所有技能值应该在0-100之间

## 输出格式（必须是有效的JSON）
{{
  "system": "COC7或DND5E",
  "name": "角色名称",
  "occupation": "职业/身份",
  "age": 25,
  "gender": "性别",
  "attributes": {{"属性1": 值, "属性2": 值}},
  "skills": {{"技能1": 值, "技能2": 值}},
  "background": "背景故事",
  "equipment": ["装备1", "装备2"],
  "notes": "其他说明",
  "confidence": {{"system": 0.9, "attributes": 0.6, "skills": 0.8}}
}}

## 文档内容
{document_text}

请直接返回JSON，不要有任何额外文本。"""

        try:
            # 调用LLM
            response = await gen_openai_chat_response(
                messages=[
                    {
                        "role": "system",
                        "content": "你是TRPG角色提取专家，必须返回有效的JSON格式。"
                    },
                    {
                        "role": "user",
                        "content": extraction_prompt
                    }
                ]
            )

            # 解析JSON
            response_text = response.response_text.strip()

            # 尝试清理响应文本（移除可能的markdown代码块）
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            if response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            response_text = response_text.strip()

            extracted_info = json.loads(response_text)
            return extracted_info

        except json.JSONDecodeError as e:
            return {
                "error": f"JSON解析失败: {str(e)}",
                "system": "CoC",
                "name": "未命名角色",
                "attributes": {},
                "skills": {}
            }
        except Exception as e:
            return {
                "error": f"提取失败: {str(e)}",
                "system": "CoC",
                "name": "未命名角色",
                "attributes": {},
                "skills": {}
            }

    def auto_complete_attributes(self, character_info: Dict, system: str) -> Dict:
        """
        自动补全缺失的属性

        Args:
            character_info: 提取的角色信息
            system: 游戏系统 ("CoC" 或 "DnD5e")

        Returns:
            补全后的属性字典
        """
        attributes = character_info.get("attributes", {})

        if system == "CoC":
            # COC7补全
            completed_attrs = self.coc7_attributes.copy()

            # 更新提取到的属性
            for attr_name, attr_value in attributes.items():
                # 标准化属性名
                std_attr = attr_name.upper()
                if std_attr in completed_attrs:
                    completed_attrs[std_attr] = int(attr_value)

            # 计算衍生属性
            completed_attrs["SAN"] = completed_attrs.get("POW", 50)
            completed_attrs["SANMAX"] = completed_attrs["SAN"]
            completed_attrs["HP"] = completed_attrs.get("SIZ", 50) // 10 + completed_attrs.get("CON", 50) // 10
            completed_attrs["HPMAX"] = completed_attrs["HP"]
            completed_attrs["MP"] = completed_attrs.get("POW", 50) // 5
            completed_attrs["MPMAX"] = completed_attrs["MP"]

            return completed_attrs

        elif system == "DnD5e":
            # DND5E补全
            completed_attrs = self.dnd5e_attributes.copy()

            for attr_name, attr_value in attributes.items():
                # 标准化属性名
                if attr_name in completed_attrs:
                    completed_attrs[attr_name] = int(attr_value)

            return completed_attrs

        return attributes

    def auto_complete_skills(self, character_info: Dict, system: str,
                            occupation: str = "", attributes: Dict = None) -> Dict:
        """
        自动补全技能

        Args:
            character_info: 提取的角色信息
            system: 游戏系统
            occupation: 职业
            attributes: 角色属性（用于推断）

        Returns:
            补全后的技能字典
        """
        skills = character_info.get("skills", {})

        if system == "CoC":
            # 使用COC7标准技能池
            completed_skills = self.coc7_skills.copy()

            # 更新提取到的技能值
            for skill_name, skill_value in skills.items():
                # 查找匹配的标准技能名
                for std_skill in completed_skills.keys():
                    if skill_name in std_skill or std_skill in skill_name:
                        completed_skills[std_skill] = int(skill_value)
                        break

            # 根据职业推荐关键技能加成
            occupation_lower = occupation.lower()
            if "侦探" in occupation_lower or "侦查" in occupation_lower:
                completed_skills["侦查"] = min(100, completed_skills.get("侦查", 25) + 15)
                completed_skills["聆听"] = min(100, completed_skills.get("聆听", 20) + 10)
            elif "医生" in occupation_lower or "医学" in occupation_lower:
                completed_skills["医学"] = min(100, completed_skills.get("医学", 1) + 40)
                completed_skills["急救"] = min(100, completed_skills.get("急救", 30) + 20)
            elif "学者" in occupation_lower or "教授" in occupation_lower:
                completed_skills["图书馆"] = min(100, completed_skills.get("图书馆", 20) + 30)
                completed_skills["克苏鲁神话"] = min(100, completed_skills.get("克苏鲁神话", 0) + 20)

            return completed_skills

        elif system == "DnD5e":
            # DND5E技能保持原样（通常在职业中定义）
            return skills

        return skills

    async def build_character_sheet(self, document_text: str, system: Optional[str] = None) -> Tuple[CharacterSheet, Dict]:
        """
        从文档构建完整的角色卡

        Args:
            document_text: 文档内容
            system: 可选的游戏系统指定

        Returns:
            (完整的CharacterSheet对象, 元数据字典)
        """
        # 第1步：提取角色信息
        extracted_info = await self.extract_character_info(document_text)

        if "error" in extracted_info:
            # 如果提取失败，返回基础角色卡
            basic_character = CharacterSheet(name="从文档导入", system=self.detect_game_system(document_text, system))
            return basic_character, {"error": extracted_info.get("error")}

        # 第2步：识别游戏系统
        detected_system = extracted_info.get("system", "CoC")
        game_system = "CoC" if "coc" in detected_system.lower() else "DnD5e"

        # 第3步：创建角色卡基础对象
        character_name = extracted_info.get("name", "未命名角色")
        character = CharacterSheet(name=character_name, system=game_system)

        # 第4步：补全属性
        character.attributes = self.auto_complete_attributes(extracted_info, game_system)

        # 第5步：补全技能
        occupation = extracted_info.get("occupation", "")
        character.skills = self.auto_complete_skills(extracted_info, game_system, occupation, character.attributes)

        # 第6步：填充其他信息
        character.occupation = occupation
        character.age = extracted_info.get("age", 25)
        character.background = extracted_info.get("background", "")
        character.equipment = extracted_info.get("equipment", [])
        character.notes = extracted_info.get("notes", "")

        # 生成元数据
        metadata = {
            "source": "file",
            "extracted_info": extracted_info,
            "confidence": extracted_info.get("confidence", {}),
            "extraction_time": datetime.now().isoformat()
        }

        return character, metadata

    def format_preview(self, character: CharacterSheet, metadata: Dict) -> str:
        """
        格式化角色卡预览

        Args:
            character: CharacterSheet对象
            metadata: 元数据

        Returns:
            格式化的预览字符串
        """
        preview_lines = [
            "📋 角色卡预览",
            "=" * 50,
            f"",
            f"👤 **基础信息**",
            f"• 姓名: {character.name}",
            f"• 系统: {character.system}",
            f"• 职业: {character.occupation or '未设定'}",
            f"• 年龄: {character.age}岁",
            f""
        ]

        # 属性预览
        if character.system == "CoC":
            preview_lines.extend([
                f"💪 **属性** (COC7标准)",
                f"STR:{character.attributes.get('STR', 50):>2} "
                f"CON:{character.attributes.get('CON', 50):>2} "
                f"DEX:{character.attributes.get('DEX', 50):>2} "
                f"INT:{character.attributes.get('INT', 50):>2}",
                f"SAN:{character.attributes.get('SAN', 50):>2} "
                f"HP:{character.attributes.get('HP', 10):>2} "
                f"MP:{character.attributes.get('MP', 10):>2}",
                f""
            ])
        elif character.system == "DnD5e":
            attrs_str = " ".join([f"{k}:{v}" for k, v in character.attributes.items()])
            preview_lines.extend([
                f"💪 **属性** (DND5E标准)",
                f"{attrs_str}",
                f""
            ])

        # 技能预览（只显示前10个）
        if character.skills:
            preview_lines.append("🔧 **核心技能** (显示前10个)")
            sorted_skills = sorted(character.skills.items(), key=lambda x: x[1], reverse=True)[:10]
            for skill_name, skill_value in sorted_skills:
                preview_lines.append(f"  • {skill_name}: {skill_value}")
            preview_lines.append("")

        # 背景故事预览
        if character.background:
            background_preview = character.background[:200] + ("..." if len(character.background) > 200 else "")
            preview_lines.extend([
                f"📖 **背景故事**",
                f"{background_preview}",
                f""
            ])

        # 置信度信息
        confidence = metadata.get("confidence", {})
        if confidence:
            preview_lines.extend([
                f"🎯 **AI置信度**",
                f"• 系统识别: {confidence.get('system', 0.8):.0%}",
                f"• 属性补全: {confidence.get('attributes', 0.6):.0%}",
                f"• 技能补全: {confidence.get('skills', 0.8):.0%}",
                f""
            ])

        preview_lines.extend([
            "=" * 50,
            "✅ 是否创建此角色？"
        ])

        return "\n".join(preview_lines)

    def store_temp_character(self, character: CharacterSheet, metadata: Dict) -> str:
        """
        临时存储角色卡，返回临时ID

        Args:
            character: CharacterSheet对象
            metadata: 元数据

        Returns:
            临时ID
        """
        temp_id = str(uuid.uuid4())[:8]
        self.temp_characters[temp_id] = {
            "character": character,
            "metadata": metadata,
            "created_time": time.time()
        }

        # 清理过期的临时角色（超过30分钟）
        current_time = time.time()
        expired_ids = [
            tid for tid, data in self.temp_characters.items()
            if current_time - data["created_time"] > 1800
        ]
        for expired_id in expired_ids:
            del self.temp_characters[expired_id]

        return temp_id

    def get_temp_character(self, temp_id: str) -> Optional[Tuple[CharacterSheet, Dict]]:
        """
        获取临时存储的角色卡

        Args:
            temp_id: 临时ID

        Returns:
            (CharacterSheet, metadata) 或 None
        """
        if temp_id in self.temp_characters:
            data = self.temp_characters[temp_id]
            return data["character"], data["metadata"]
        return None

    def remove_temp_character(self, temp_id: str):
        """删除临时角色卡"""
        if temp_id in self.temp_characters:
            del self.temp_characters[temp_id]
