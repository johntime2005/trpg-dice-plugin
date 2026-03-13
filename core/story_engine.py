"""
智能剧情引擎

动态生成剧情、场景描述，根据玩家行动即兴创作
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum


class TensionLevel(Enum):
    """剧情紧张度"""
    CALM = 1
    CURIOUS = 3
    TENSE = 5
    DANGEROUS = 7
    CRITICAL = 9


class SceneMood(Enum):
    """场景氛围"""
    PEACEFUL = "平静"
    MYSTERIOUS = "神秘"
    HORROR = "恐怖"
    EPIC = "史诗"
    MELANCHOLY = "忧郁"


@dataclass
class PlotState:
    """剧情状态"""
    current_scene: str = "未知场景"
    tension_level: TensionLevel = TensionLevel.CALM
    scene_mood: SceneMood = SceneMood.PEACEFUL
    active_clues: List[str] = None
    pending_events: List[str] = None
    
    def __post_init__(self):
        if self.active_clues is None:
            self.active_clues = []
        if self.pending_events is None:
            self.pending_events = []


class StoryEngine:
    """智能剧情引擎"""
    
    def __init__(self, store):
        self.store = store
    
    async def get_plot_state(self, chat_key: str) -> PlotState:
        """获取当前剧情状态"""
        data = await self.store.get(store_key=f"plot_state.{chat_key}")
        if not data:
            return PlotState()
        
        import json
        state_dict = json.loads(data)
        return PlotState(
            current_scene=state_dict.get("current_scene", "未知场景"),
            tension_level=TensionLevel(state_dict.get("tension_level", 1)),
            scene_mood=SceneMood(state_dict.get("scene_mood", "平静")),
            active_clues=state_dict.get("active_clues", []),
            pending_events=state_dict.get("pending_events", [])
        )
    
    async def update_plot_state(self, chat_key: str, state: PlotState):
        """更新剧情状态"""
        import json
        state_dict = {
            "current_scene": state.current_scene,
            "tension_level": state.tension_level.value,
            "scene_mood": state.scene_mood.value,
            "active_clues": state.active_clues,
            "pending_events": state.pending_events
        }
        await self.store.set(store_key=f"plot_state.{chat_key}", value=json.dumps(state_dict))
    
    async def add_clue(self, chat_key: str, clue: str):
        """添加线索"""
        state = await self.get_plot_state(chat_key)
        if clue not in state.active_clues:
            state.active_clues.append(clue)
            await self.update_plot_state(chat_key, state)
    
    async def set_tension(self, chat_key: str, level: TensionLevel):
        """设置紧张度"""
        state = await self.get_plot_state(chat_key)
        state.tension_level = level
        await self.update_plot_state(chat_key, state)
    
    async def set_scene(self, chat_key: str, scene: str, mood: SceneMood):
        """设置场景"""
        state = await self.get_plot_state(chat_key)
        state.current_scene = scene
        state.scene_mood = mood
        await self.update_plot_state(chat_key, state)
