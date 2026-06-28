"""自定义规则系统 - 支持私人玩法的灵活规则定义"""

import json
from typing import Any, Dict, List


class CustomRuleSystem:
    def __init__(self, store):
        self.store = store

    async def define_custom_rule(
        self, chat_key: str, rule_name: str, rule_description: str, examples: str = ""
    ) -> bool:
        rules = await self._get_rules(chat_key)
        rules[rule_name] = {"description": rule_description, "examples": examples}
        await self._save_rules(chat_key, rules)
        return True

    async def define_custom_attribute(
        self, chat_key: str, attr_name: str, attr_type: str, default_value: str, description: str
    ) -> bool:
        attrs = await self._get_attributes(chat_key)
        attrs[attr_name] = {"type": attr_type, "default": default_value, "description": description}
        await self._save_attributes(chat_key, attrs)
        return True

    async def upsert_check_metric(self, chat_key: str, metric_id: str, metric: Dict[str, Any]) -> Dict[str, Any]:
        check_index = await self.get_check_index(chat_key)
        normalized = self._normalize_check_metric(metric_id, metric)
        check_index[normalized["id"]] = normalized
        await self.save_check_index(chat_key, check_index)
        return normalized

    async def remove_check_metric(self, chat_key: str, metric_id: str) -> bool:
        check_index = await self.get_check_index(chat_key)
        if metric_id not in check_index:
            return False
        del check_index[metric_id]
        await self.save_check_index(chat_key, check_index)
        return True

    async def get_check_index(self, chat_key: str) -> Dict[str, Dict[str, Any]]:
        data = await self.store.get(store_key=f"check_index.{chat_key}")
        if not data:
            return {}
        parsed = json.loads(data)
        if not isinstance(parsed, dict):
            return {}
        return {str(key): value for key, value in parsed.items() if isinstance(value, dict)}

    async def save_check_index(self, chat_key: str, check_index: Dict[str, Dict[str, Any]]):
        await self.store.set(store_key=f"check_index.{chat_key}", value=json.dumps(check_index, ensure_ascii=False))

    async def get_check_index_prompt(self, chat_key: str) -> str:
        check_index = await self.get_check_index(chat_key)
        if not check_index:
            return """# TRPG判定索引 JSON
当前频道还没有结构化判定索引。需要长期复用某个判定指标时，调用 upsert_check_metric 记录为 JSON。"""

        parts = [
            "# TRPG判定索引 JSON",
            "以下是当前频道可复用的结构化判定指标。需要检定时，优先按 system/category/tags/attribute/skill 匹配指标，再调用 request_player_roll。",
            "字段含义: id/name/system/category/dice_expression/attribute/skill/default_target/difficulty/modifiers/success_rule/failure_rule/examples/tags/notes",
            "```json",
            json.dumps(check_index, ensure_ascii=False, indent=2),
            "```",
        ]
        return "\n".join(parts)

    async def get_custom_rules_prompt(self, chat_key: str) -> str:
        rules = await self._get_rules(chat_key)
        attrs = await self._get_attributes(chat_key)
        check_index_prompt = await self.get_check_index_prompt(chat_key)

        if not rules and not attrs:
            if "还没有结构化判定索引" in check_index_prompt:
                return ""
            return check_index_prompt

        parts = ["# 自定义规则、属性和判定索引"]

        if check_index_prompt and "还没有结构化判定索引" not in check_index_prompt:
            parts.append(check_index_prompt)

        if not rules and not attrs:
            return "\n\n".join(parts)

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

    async def get_check_index_schema_prompt(self) -> str:
        return """# TRPG结构化主持记录格式
你应像笔记软件一样维护结构化 JSON，而不是只用自然语言记忆。需要长期复用的地图、场景、战斗、判定指标都应写入 JSON。

## 判定索引 check_metric
使用 upsert_check_metric 写入 JSON，字段建议如下：
```json
{
  "id": "唯一ID，例如 coc_spot_hidden",
  "name": "判定名称，例如 侦察",
  "system": "适用系统，例如 CoC/DnD5e/通用",
  "category": "类别，例如 感知/社交/战斗/知识/理智",
  "dice_expression": "推荐骰式，例如 1d100 / d20+3",
  "attribute": "关联属性，例如 INT/DEX/WIS",
  "skill": "关联技能，例如 侦察/图书馆使用/Stealth",
  "default_target": "默认目标值或 DC，例如 60 / DC 15",
  "difficulty": "难度分层说明，例如 普通/困难/极难 或 DC 10/15/20",
  "modifiers": ["常见修正，例如 黑暗环境 -20", "有工具 +2"],
  "success_rule": "成功时如何解释",
  "failure_rule": "失败时如何解释",
  "examples": ["使用示例"],
  "tags": ["检索标签"],
  "notes": "额外说明"
}
```
调用时先匹配 JSON 指标，再创建 request_player_roll，不要临时猜测不存在的指标。"""

    async def get_host_state(self, chat_key: str) -> Dict[str, Any]:
        data = await self.store.get(store_key=f"host_state.{chat_key}")
        if not data:
            return self._default_host_state()
        parsed = json.loads(data)
        if not isinstance(parsed, dict):
            return self._default_host_state()
        default_state = self._default_host_state()
        default_state.update(parsed)
        return default_state

    async def save_host_state(self, chat_key: str, host_state: Dict[str, Any]):
        await self.store.set(store_key=f"host_state.{chat_key}", value=json.dumps(host_state, ensure_ascii=False))

    async def upsert_map_scene(self, chat_key: str, scene_id: str, scene: Dict[str, Any]) -> Dict[str, Any]:
        host_state = await self.get_host_state(chat_key)
        normalized = self._normalize_map_scene(scene_id, scene)
        host_state.setdefault("maps", {})[normalized["id"]] = normalized
        host_state["active_map_id"] = normalized["id"]
        host_state["mode"] = "exploration"
        await self.save_host_state(chat_key, host_state)
        return normalized

    async def set_active_scene(self, chat_key: str, scene_id: str) -> bool:
        host_state = await self.get_host_state(chat_key)
        maps = host_state.setdefault("maps", {})
        if scene_id not in maps:
            return False
        host_state["active_map_id"] = scene_id
        host_state["mode"] = "exploration"
        await self.save_host_state(chat_key, host_state)
        return True

    async def start_combat(self, chat_key: str, combat: Dict[str, Any]) -> Dict[str, Any]:
        host_state = await self.get_host_state(chat_key)
        participants = combat.get("participants") or []
        normalized_participants = []
        for item in participants:
            if isinstance(item, dict):
                normalized_participants.append(
                    {
                        "id": str(item.get("id") or item.get("name") or "").strip(),
                        "name": str(item.get("name") or item.get("id") or "").strip(),
                        "side": str(item.get("side") or "neutral").strip(),
                        "speed": self._safe_int(item.get("speed"), 0),
                        "initiative": self._safe_int(item.get("initiative"), self._safe_int(item.get("speed"), 0)),
                        "hp": item.get("hp", ""),
                        "status": self._ensure_list(item.get("status")),
                        "notes": str(item.get("notes") or "").strip(),
                    }
                )
        normalized_participants.sort(key=lambda item: (item["initiative"], item["speed"]), reverse=True)
        combat_state = {
            "id": str(combat.get("id") or f"combat_{int(__import__('time').time())}").strip(),
            "name": str(combat.get("name") or "未命名战斗").strip(),
            "round": self._safe_int(combat.get("round"), 1),
            "turn_index": 0,
            "sort_rule": str(combat.get("sort_rule") or "initiative_then_speed_desc").strip(),
            "participants": normalized_participants,
            "battlefield": str(combat.get("battlefield") or host_state.get("active_map_id") or "").strip(),
            "objectives": self._ensure_list(combat.get("objectives")),
            "notes": str(combat.get("notes") or "").strip(),
        }
        host_state["mode"] = "combat"
        host_state["combat"] = combat_state
        await self.save_host_state(chat_key, host_state)
        return combat_state

    async def advance_combat_turn(self, chat_key: str) -> Dict[str, Any]:
        host_state = await self.get_host_state(chat_key)
        combat = host_state.get("combat") or {}
        participants = combat.get("participants") or []
        if not participants:
            raise ValueError("当前没有战斗参与者")

        turn_index = int(combat.get("turn_index") or 0) + 1
        round_no = int(combat.get("round") or 1)
        if turn_index >= len(participants):
            turn_index = 0
            round_no += 1
        combat["turn_index"] = turn_index
        combat["round"] = round_no
        host_state["mode"] = "combat"
        host_state["combat"] = combat
        await self.save_host_state(chat_key, host_state)
        return combat

    async def end_combat(self, chat_key: str) -> Dict[str, Any]:
        host_state = await self.get_host_state(chat_key)
        combat = host_state.get("combat") or {}
        host_state["mode"] = "exploration"
        host_state["last_combat"] = combat
        host_state["combat"] = {}
        await self.save_host_state(chat_key, host_state)
        return combat

    async def get_host_state_prompt(self, chat_key: str) -> str:
        host_state = await self.get_host_state(chat_key)
        maps = host_state.get("maps") or {}
        combat = host_state.get("combat") or {}
        if not maps and not combat:
            return """# TRPG主持状态 JSON
当前还没有结构化场景/战斗状态。主持时应使用 upsert_map_scene 记录地图场景；进入战斗时使用 start_combat 按速度/先攻排序开启回合制。"""

        return "\n".join(
            [
                "# TRPG主持状态 JSON",
                "mode=exploration 时按地图/普通场景推进；mode=combat 时按 combat.participants 顺序进行回合制。",
                "进入新地图或普通场景时维护 maps/active_map_id；进入战斗时维护 combat.round/turn_index/participants。",
                "```json",
                json.dumps(host_state, ensure_ascii=False, indent=2),
                "```",
            ]
        )

    def _default_host_state(self) -> Dict[str, Any]:
        return {
            "mode": "exploration",
            "active_map_id": "",
            "maps": {},
            "combat": {},
            "last_combat": {},
        }

    def _normalize_map_scene(self, scene_id: str, scene: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": str(scene.get("id") or scene_id).strip(),
            "name": str(scene.get("name") or scene_id).strip(),
            "type": str(scene.get("type") or "map").strip(),
            "mood": str(scene.get("mood") or "").strip(),
            "description": str(scene.get("description") or "").strip(),
            "exits": scene.get("exits") if isinstance(scene.get("exits"), dict) else {},
            "npcs": self._ensure_list(scene.get("npcs")),
            "clues": self._ensure_list(scene.get("clues")),
            "hazards": self._ensure_list(scene.get("hazards")),
            "available_checks": self._ensure_list(scene.get("available_checks")),
            "notes": str(scene.get("notes") or "").strip(),
        }

    def _normalize_check_metric(self, metric_id: str, metric: Dict[str, Any]) -> Dict[str, Any]:
        normalized = {
            "id": str(metric.get("id") or metric_id).strip(),
            "name": str(metric.get("name") or metric_id).strip(),
            "system": str(metric.get("system") or "通用").strip(),
            "category": str(metric.get("category") or "general").strip(),
            "dice_expression": str(metric.get("dice_expression") or metric.get("dice") or "1d100").strip(),
            "attribute": str(metric.get("attribute") or "").strip(),
            "skill": str(metric.get("skill") or "").strip(),
            "default_target": str(metric.get("default_target") or "").strip(),
            "difficulty": metric.get("difficulty") or "",
            "modifiers": self._ensure_list(metric.get("modifiers")),
            "success_rule": str(metric.get("success_rule") or "").strip(),
            "failure_rule": str(metric.get("failure_rule") or "").strip(),
            "examples": self._ensure_list(metric.get("examples")),
            "tags": self._ensure_list(metric.get("tags")),
            "notes": str(metric.get("notes") or "").strip(),
        }
        if not normalized["id"]:
            raise ValueError("判定指标 id 不能为空")
        return normalized

    def _ensure_list(self, value: Any) -> List[str]:
        if value is None or value == "":
            return []
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        return [str(value).strip()]

    def _safe_int(self, value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    async def _get_rules(self, chat_key: str) -> Dict:
        data = await self.store.get(store_key=f"custom_rules.{chat_key}")
        return json.loads(data) if data else {}

    async def _save_rules(self, chat_key: str, rules: Dict):
        await self.store.set(store_key=f"custom_rules.{chat_key}", value=json.dumps(rules, ensure_ascii=False))

    async def _get_attributes(self, chat_key: str) -> Dict:
        data = await self.store.get(store_key=f"custom_attrs.{chat_key}")
        return json.loads(data) if data else {}

    async def _save_attributes(self, chat_key: str, attrs: Dict):
        await self.store.set(store_key=f"custom_attrs.{chat_key}", value=json.dumps(attrs, ensure_ascii=False))
