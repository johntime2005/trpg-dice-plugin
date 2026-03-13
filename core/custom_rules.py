"""自定义规则系统 - 支持私人玩法的灵活规则定义"""

from typing import Dict, List, Optional
import json


class CustomRuleSystem:
    def __init__(self, store):
        self.store = store
    
    async def define_custom_rule(self, chat_key: str, rule_name: str, 
                                 rule_description: str, examples: str = "") -> bool:
        rules = await self._get_rules(chat_key)
        rules[rule_name] = {
            "description": rule_description,
            "examples": examples
        }
        await self._save_rules(chat_key, rules)
        return True
    
    async def define_custom_attribute(self, chat_key: str, attr_name: str,
                                     attr_type: str, default_value: str,
                                     description: str) -> bool:
        attrs = await self._get_attributes(chat_key)
        attrs[attr_name] = {
            "type": attr_type,
            "default": default_value,
            "description": description
        }
        await self._save_attributes(chat_key, attrs)
        return True
    
    async def get_custom_rules_prompt(self, chat_key: str) -> str:
        rules = await self._get_rules(chat_key)
        attrs = await self._get_attributes(chat_key)
        
        if not rules and not attrs:
            return ""
        
        parts = ["# 自定义规则和属性"]
        
        if rules:
            parts.append("\n## 自定义规则:")
            for name, data in rules.items():
                parts.append(f"### {name}")
                parts.append(data["description"])
                if data.get("examples"):
                    parts.append(f"示例: {data['examples']}")
        
        if attrs:
            parts.append("\n## 自定义属性:")
            for name, data in attrs.items():
                parts.append(f"• {name} ({data['type']}): {data['description']}")
                parts.append(f"  默认值: {data['default']}")
        
        return "\n".join(parts)
    
    async def _get_rules(self, chat_key: str) -> Dict:
        data = await self.store.get(store_key=f"custom_rules.{chat_key}")
        return json.loads(data) if data else {}
    
    async def _save_rules(self, chat_key: str, rules: Dict):
        await self.store.set(store_key=f"custom_rules.{chat_key}", 
                            value=json.dumps(rules, ensure_ascii=False))
    
    async def _get_attributes(self, chat_key: str) -> Dict:
        data = await self.store.get(store_key=f"custom_attrs.{chat_key}")
        return json.loads(data) if data else {}
    
    async def _save_attributes(self, chat_key: str, attrs: Dict):
        await self.store.set(store_key=f"custom_attrs.{chat_key}", 
                            value=json.dumps(attrs, ensure_ascii=False))
