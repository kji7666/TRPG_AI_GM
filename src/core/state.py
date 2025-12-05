import os
import json
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
# 確保這個 import 路徑對應到你放置 models.py 的位置
from ..scenarios.models import Scenario
from src.util.logger import logger

# --- 1. 玩家屬性 ---
class PlayerStats(BaseModel):
    STR: int = 50
    CON: int = 50
    SIZ: int = 50
    DEX: int = 50
    APP: int = 50
    EDU: int = 50
    INT: int = 50
    POW: int = 50
    LUCK: int = 50
    
    HP: int = 10
    MP: int = 10
    SAN: int = 50
    MOV: int = 8
    
    # Coc7h 特殊屬性
    DAMAGE: int = Field(default=0, alias="db") 
    BUILD: int = 0 

class PlayerState(BaseModel):
    model_config = {"validate_assignment": True} 
    name: str = "調查員"
    stats: PlayerStats = Field(default_factory=PlayerStats)
    skills: Dict[str, int] = Field(default_factory=dict)
    # 背包現在只存 Item ID (例如 "driver_key")
    inventory: List[str] = Field(default_factory=list)
    attributes: Dict[str, Any] = Field(default_factory=dict)

# --- 2. NPC 狀態 ---
class NPCState(BaseModel):
    # 靜態屬性 (從 Scenario 複製過來，方便存檔時保留快照)
    id: str
    name: str
    description: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    dialogue_style: Optional[str] = None
    
    # 動態屬性 (遊戲中會變的)
    status: str = "alive"
    location: str
    relation: int = 50
    flags: Dict[str, Any] = Field(default_factory=dict)

# --- 3. 世界狀態 ---
class WorldState(BaseModel):
    model_config = {"validate_assignment": True} 
    turn_count: int = 0
    current_node_id: str = "car_6"
    # 記錄哪些 Item ID 被拿走了
    taken_items: Dict[str, bool] = Field(default_factory=dict)
    # 全局變數
    flags: Dict[str, Any] = Field(default_factory=dict)
    # NPC 實例
    npcs: Dict[str, NPCState] = Field(default_factory=dict)
    # 長期記憶摘要
    history_summary: str = "遊戲開始。調查員在末班電車上醒來。" 
    visited_nodes: List[str] = Field(default_factory=list)

# --- 4. 遊戲總狀態 ---
class GameState(BaseModel):
    player: PlayerState
    world: WorldState = Field(default_factory=WorldState)
    
    # Scenario 是靜態資料，不參與 Pydantic 的序列化 (exclude=True)
    # 但我們需要它來查表 (ID -> Name)
    scenario: Optional[Scenario] = Field(default=None, exclude=True)

    def to_json(self) -> str:
        """
        回傳給 LLM 看的精簡版 JSON。
        關鍵功能：將 ID 翻譯成人類可讀的 Name。
        """
        logger.log("[GameState.to_json] Converting state to JSON for LLM", "system.txt")
        
        # 1. 篩選重要技能
        important_skills = {
            k: v for k, v in self.player.skills.items() 
            if v > 20 or k in ["偵查", "聆聽", "急救", "心理學", "Spot Hidden", "Listen", "閃避", "Dodge"]
        }

        # 2. 翻譯背包物品 (ID -> Name)
        inventory_display = []
        if self.scenario:
            for item_raw in self.player.inventory:
                # [修復] 防呆處理：AI 可能塞了 Dict 進來，我們嘗試提取 ID 或轉字串
                query_id = item_raw
                
                # 如果是字典，嘗試抓 'id' 或 'name'，否則轉字串
                if isinstance(item_raw, dict):
                    query_id = item_raw.get("id", item_raw.get("name", str(item_raw)))
                
                # 確保 query_id 是字串才能查表
                if isinstance(query_id, str) and query_id in self.scenario.items:
                    item_def = self.scenario.items[query_id]
                    inventory_display.append(item_def.name)
                else:
                    # 查不到或格式奇怪，直接顯示轉字串的結果 (避免崩潰)
                    inventory_display.append(str(query_id))
        else:
            inventory_display = [str(i) for i in self.player.inventory]

        # 3. 翻譯當前地點 (ID -> Name)
        location_display = self.world.current_node_id
        if self.scenario and self.world.current_node_id in self.scenario.nodes:
            location_display = self.scenario.nodes[self.world.current_node_id].name

        # 4. 組裝玩家數據
        simplified_player = {
            "name": self.player.name,
            "hp": self.player.stats.HP,
            "san": self.player.stats.SAN,
            "str": self.player.stats.STR,
            "dex": self.player.stats.DEX, # DEX 對戰鬥和閃避很重要，建議加上
            "inventory": inventory_display, # 這裡是翻譯過的名字
            "important_skills": important_skills
        }

        # 5. 組裝世界數據
        simplified_world = {
            "location": location_display, # 這裡是翻譯過的名字
            "turn": self.world.turn_count,
            "flags": self.world.flags,
            "memory": self.world.history_summary
        }

        summary = {
            "player": simplified_player,
            "world": simplified_world
        }
        
        return json.dumps(summary, ensure_ascii=False)

    # --- 存檔功能 ---
    def save_to_file(self, filename: str = "savegame.json"):
        logger.log("[GameState.save_to_file]", "system.txt")
        save_dir = "data/saves"
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        file_path = os.path.join(save_dir, filename)
        # 排除 scenario，只存動態數據
        json_str = self.model_dump_json(indent=2, exclude={'scenario'})
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        return f"遊戲已儲存至 {file_path}"

    # --- 讀檔功能 ---
    @classmethod 
    def load_from_file(cls, scenario: Scenario, filename: str = "savegame.json") -> 'GameState':
        logger.log("[GameState.load_from_file]", "system.txt")
        file_path = os.path.join("data/saves", filename)
        
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"找不到存檔: {file_path}")
            
        with open(file_path, "r", encoding="utf-8") as f:
            json_str = f.read()
            
        # 還原數據
        game = cls.model_validate_json(json_str)
        # 重要：重新掛載 Scenario 物件，因為存檔裡沒有
        game.scenario = scenario
        
        return game