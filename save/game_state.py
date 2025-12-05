# src/core/game_state.py
from pydantic import BaseModel, Field
from typing import List, Dict, Optional

# 定義玩家屬性
class PlayerState(BaseModel):
    name: str = "調查員"
    hp: int = 12
    san: int = 50
    str_val: int = 50  # 力量
    dex_val: int = 50  # 敏捷
    # 技能表
    skills: Dict[str, int] = Field(default_factory=lambda: {"偵查": 25, "聆聽": 20})
    # 背包 (存放 Item ID)
    inventory: List[str] = Field(default_factory=list)

# 定義整個遊戲的運行狀態
class GameState:
    def __init__(self, scenario):
        self.scenario = scenario
        # 初始化玩家
        self.player = PlayerState()
        # 當前位置 ID
        self.current_node_id = scenario.start_node_id
        # 記錄世界變動 (例如: "note" 被拿走了 -> taken_items=["note"])
        self.taken_items: List[str] = []

    @property
    def current_node(self):
        """取得當前房間的詳細資料"""
        return self.scenario.nodes[self.current_node_id]

    def move(self, direction: str) -> bool:
        """嘗試移動"""
        exits = self.current_node.exits
        if direction in exits:
            self.current_node_id = exits[direction]
            return True
        return False

    def take_item(self, item_name_or_id: str) -> str:
        """嘗試拿取物品，回傳訊息"""
        # 尋找當前房間的物品
        target_item = None
        for item in self.current_node.items:
            # 檢查物品 ID 是否已經在被拿取的列表中
            if item.id in self.taken_items:
                continue
            
            # 比對名稱或 ID
            if item.name == item_name_or_id or item.id == item_name_or_id:
                target_item = item
                break
        
        if target_item:
            if target_item.is_takeable:
                self.taken_items.append(target_item.id)
                self.player.inventory.append(target_item.name)
                return f"你拿起了 [{target_item.name}]。"
            else:
                return f"[{target_item.name}] 看起來拿不走。"
        
        return "這裡沒有這個東西。"