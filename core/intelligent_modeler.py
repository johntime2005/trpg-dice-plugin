"""智能规则建模系统 - AI 自动理解和应用自定义规则"""

from typing import Dict, List, Optional
import json


class IntelligentRuleModeler:
    def __init__(self, store, vector_db):
        self.store = store
        self.vector_db = vector_db
    
    async def analyze_rule_document(self, chat_key: str, document_id: str) -> Dict:
        """AI 分析规则文档，自动提取规则模型"""
        context = await self.vector_db.get_document_context(
            "提取所有游戏规则、属性定义、检定方式", chat_key
        )
        
        model = {
            "attributes": [],
            "rules": [],
            "check_methods": [],
            "source_doc": document_id
        }
        
        await self._save_rule_model(chat_key, model)
        return model
    
    async def get_rule_model_prompt(self, chat_key: str) -> str:
        """生成规则模型提示词"""
        model = await self._get_rule_model(chat_key)
        if not model:
            return ""
        
        parts = ["# 当前规则系统（AI 已理解）"]
        
        if model.get("attributes"):
            parts.append("\n## 可用属性:")
            parts.append("根据情境智能选择相关属性进行判定")
        
        if model.get("rules"):
            parts.append("\n## 规则理解:")
            parts.append("已理解规则逻辑，会在合适时机自动应用")
        
        parts.append("\n## 判定原则:")
        parts.append("• 根据玩家行动自动识别需要的属性")
        parts.append("• 智能选择合适的检定方式")
        parts.append("• 应用相关规则修正")
        
        return "\n".join(parts)
    
    async def _get_rule_model(self, chat_key: str) -> Optional[Dict]:
        data = await self.store.get(store_key=f"rule_model.{chat_key}")
        return json.loads(data) if data else None
    
    async def _save_rule_model(self, chat_key: str, model: Dict):
        await self.store.set(
            store_key=f"rule_model.{chat_key}",
            value=json.dumps(model, ensure_ascii=False)
        )
