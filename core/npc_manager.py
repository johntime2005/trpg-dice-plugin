"""NPC 管理系统"""

from typing import Dict, List, Optional
from dataclasses import dataclass, field
import json


@dataclass
class NPC:
    npc_id: str
    name: str
    personality: str
    background: str
    secrets: List[str] = field(default_factory=list)
    relationships: Dict[str, int] = field(default_factory=dict)
    memory: List[str] = field(default_factory=list)
    current_mood: str = "中立"


class NPCManager:
    def __init__(self, store):
        self.store = store
    
    async def create_npc(self, chat_key: str, npc_id: str, name: str, 
                        personality: str, background: str, secrets: List[str] = None) -> NPC:
        npc = NPC(
            npc_id=npc_id,
            name=name,
            personality=personality,
            background=background,
            secrets=secrets or []
        )
        await self._save_npc(chat_key, npc)
        return npc
    
    async def get_npc(self, chat_key: str, npc_id: str) -> Optional[NPC]:
        data = await self.store.get(store_key=f"npc.{chat_key}.{npc_id}")
        if not data:
            return None
        npc_dict = json.loads(data)
        return NPC(**npc_dict)
    
    async def _save_npc(self, chat_key: str, npc: NPC):
        data = json.dumps({
            "npc_id": npc.npc_id,
            "name": npc.name,
            "personality": npc.personality,
            "background": npc.background,
            "secrets": npc.secrets,
            "relationships": npc.relationships,
            "memory": npc.memory,
            "current_mood": npc.current_mood
        })
        await self.store.set(store_key=f"npc.{chat_key}.{npc.npc_id}", value=data)
    
    async def add_memory(self, chat_key: str, npc_id: str, memory: str):
        npc = await self.get_npc(chat_key, npc_id)
        if npc:
            npc.memory.append(memory)
            if len(npc.memory) > 10:
                npc.memory = npc.memory[-10:]
            await self._save_npc(chat_key, npc)
    
    async def update_relationship(self, chat_key: str, npc_id: str, target: str, change: int):
        npc = await self.get_npc(chat_key, npc_id)
        if npc:
            current = npc.relationships.get(target, 0)
            npc.relationships[target] = max(-100, min(100, current + change))
            await self._save_npc(chat_key, npc)
