from typing import List, Optional
from .state import GameState
from .tools import UniversalTools
from src.util.logger import logger

class EventEngine:
    def __init__(self, game: GameState, tools: UniversalTools):
        logger.log("[EventEngine.__init__] game, tools", "system.txt")
        self.game = game
        self.tools = tools

    def check_condition(self, condition_str: str) -> bool:
        """安全評估條件 (保持不變)"""
        # logger.log("[EventEngine.check_condition] check : " + str(condition_str), "system.txt")
        if not condition_str:
            return True
        
        context = {
            "player": self.game.player,
            "world": self.game.world
        }
        
        try:
            return eval(condition_str, {"__builtins__": {}}, context)
        except Exception as e:
            print(f"⚠️ 條件評估失敗 [{condition_str}]: {e}")
            return False

    def _execute_event(self, event) -> Optional[str]:
        """
        [內部方法] 執行單一事件的邏輯 (修改狀態 + 產生訊息)
        """
        logger.log(f"[EventEngine] Triggering: {event.id}", "system.txt")
        logger.log(f"⚡ [Event] 觸發事件: {event.id}", "think.txt")

        # 1. 標記已觸發 (Once Only)
        triggered_key = f"event_triggered_{event.id}"
        if event.once_only:
            self.game.world.flags[triggered_key] = True
        
        # 2. 執行效果 (Modify State)
        if event.effect_type == "modify_state" and event.effect_params:
            result = self.tools.modify_state(**event.effect_params)
            logger.log(f"   -> {result}", "think.txt")

        # 3. 產生訊息 (Message OR Auto-RAG)
        final_message = ""
        
        # A. 如果有預設訊息，直接使用
        if event.message:
            final_message = f"【事件發生】{event.message}"
        
        # B. 如果有 narrative_tags，自動去查 RAG 補充敘事 (這是新架構的亮點)
        if event.narrative_tags:
            query = " ".join(event.narrative_tags)
            logger.log(f"[EventEngine] Auto-RAG for event: {query}", "system.txt")
            
            # 使用 tools 裡的 search_knowledge (它已經串接了 retriever)
            rag_content = self.tools.search_knowledge(query)
            
            # 將 RAG 內容標註為 GM 資訊，餵給 AI
            final_message += f"\n[事件敘事參考 (來自 RAG)]:\n{rag_content}"

        return final_message if final_message else None

    def process_events(self, trigger_type: str = "turn_end") -> List[str]:
        """
        檢查並執行 [全域事件] (Global Events)
        """
        messages = []
        
        # 檢查 Scenario 是否存在
        if not self.game.scenario:
            return []

        for event in self.game.scenario.global_events:
            # 1. 檢查觸發時機
            if event.trigger != trigger_type:
                continue
            
            # 2. 檢查是否已觸發 (Once Only)
            triggered_key = f"event_triggered_{event.id}"
            if event.once_only and self.game.world.flags.get(triggered_key):
                continue
                
            # 3. 檢查條件
            if self.check_condition(event.condition):
                msg = self._execute_event(event)
                if msg:
                    messages.append(msg)
                    
        return messages

    def process_node_events(self, node_id: str, trigger_type: str = "on_enter") -> List[str]:
        """
        [新增] 檢查並執行 [當前房間事件] (Node Events)
        通常在 main.py 玩家移動成功後呼叫
        """
        messages = []
        
        if not self.game.scenario or node_id not in self.game.scenario.nodes:
            return []

        node = self.game.scenario.nodes[node_id]
        
        for event in node.events:
            # 1. 檢查觸發時機
            if event.trigger != trigger_type:
                continue
            
            # 2. 檢查是否已觸發
            triggered_key = f"event_triggered_{event.id}"
            if event.once_only and self.game.world.flags.get(triggered_key):
                continue
            
            # 3. 檢查條件
            if self.check_condition(event.condition):
                msg = self._execute_event(event)
                if msg:
                    messages.append(msg)
        
        return messages