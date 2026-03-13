"""情境感知检定系统"""

from typing import Optional
from .story_engine import StoryEngine, TensionLevel


class ContextualCheckSystem:
    def __init__(self, story_engine: StoryEngine):
        self.story_engine = story_engine
    
    async def suggest_difficulty(self, chat_key: str, action: str, 
                                importance: str = "normal") -> int:
        plot_state = await self.story_engine.get_plot_state(chat_key)
        
        base_dc = {
            "trivial": 5,
            "easy": 10,
            "normal": 15,
            "hard": 20,
            "very_hard": 25
        }.get(importance, 15)
        
        if plot_state.tension_level.value >= 7:
            base_dc += 5
        elif plot_state.tension_level.value <= 3:
            base_dc -= 3
        
        return max(5, min(30, base_dc))
    
    async def should_require_check(self, action: str, context: str) -> bool:
        routine_actions = ["走路", "说话", "观察", "思考"]
        return not any(routine in action for routine in routine_actions)
