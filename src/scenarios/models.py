# 劇本的靜態設定
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
# Optional[T] → 表示該值可以是 None 或 T
# Any → 任意型別

# Pydantic 的優點 : 宣告欄位型別後，Pydantic 會自動檢查資料是否符合型別, 避免傳入錯誤型別，減少程式錯誤
#                   可設定欄位預設值或允許 Option None
# BaseModel → Pydantic 的基底類別，所有資料模型都繼承它
# Field → 用來設定欄位的預設值、描述或 factory

# 可互動物品定義
class ItemDef(BaseModel):
    name: str
    tags: List[str] = Field(default_factory=list) # RAG 關鍵字
    description: Optional[str] = None  # 舊版兼容，新版主要靠 RAG 描述，這裡可留空
    contains: List[str] = Field(default_factory=list) # 容器內含物品 ID (如包包)
    locked: bool = False      # 是否上鎖
    immovable: bool = False   # 是否不可拿取 (如控制台)
    # is_takeable 邏輯：如果不 immovable 且不 locked，通常就是 takeable
    #     "items": [
    #   {
    #     "id": "black_bag",
    #     "name": "黑色包包",
    #     "description": "一個背帶斷裂的黑色公事包，被壓在一個大行李箱下面。這是京山掉落的包包。",
    #     "is_takeable": true
    #   },

# 複雜出口定義 (用於處理鎖、機關)
class ComplexExit(BaseModel):
    target_node: str          # 目標房間 ID
    locked: bool = False      # 是否鎖住
    key_id: Optional[str] = None # 需要的鑰匙 Item ID
    difficulty: Optional[int] = None # 若需檢定 (如鎖匠)，難度是多少
    locked_msg: Optional[str] = None # (Optional) 鎖住時的提示，若無則 AI 生成

# Event定義
class ScriptedEvent(BaseModel):
    id: str
    trigger: str = "turn_end" # "turn_end", "on_enter"
    condition: Optional[str] = None # Python 邏輯字串 (如 "world.turn_count == 6")
    effect_type: str # "narrative", "modify_state"
    effect_params: Dict[str, Any] = Field(default_factory=dict)
    narrative_tags: List[str] = Field(default_factory=list) # 發生時讓 RAG 檢索描述用的 tags
    message: Optional[str] = None # 簡短提示 (給人類 KP 看或作為備用)
    once_only: bool = True
    #     "events": [
    #     {
    #       "id": "clicker_encounter",
    #       "name": "目擊循聲者",
    #       "trigger": "on_enter",
    #       "effect_type": "narrative",
    #       "message": "【系統強制】你目擊了違反生理常識的怪物。那頭部爆裂的模樣讓你感到生理上的不適。請進行 SAN 值檢定 (1/1d6)。",
    #       "once_only": true
    #     }
    #   ]
    #   "global_events": [
    # {
    #   "id": "tremor_warning",
    #   "name": "初期震動",
    #   "trigger": "turn_end",
    #   "condition": "world.turn_count == 3",
    #   "effect_type": "narrative",
    #   "message": "【警告】腳下的地板劇烈震動，遠處傳來金屬被扭曲的尖銳聲響。某個巨大的東西正在接近...",
    #   "once_only": true
    # },

# 3. 房間定義
class Room(BaseModel):
    id: str
    name: str
    type: str = "normal" # "safe", "hazard", "combat"
    # 敘事層：description 變為可選，主要依賴 tags 去查 RAG
    description: Optional[str] = None 
    tags: List[str] = Field(default_factory=list)
    # 邏輯層：Exits 支援字串 (簡單移動) 或 ComplexExit (鎖/機關)
    exits: Dict[str, Union[str, ComplexExit]] = Field(default_factory=dict)
    # 邏輯層：Items 現在只存 ID 列表，具體資料去查 Scenario.items
    items: List[str] = Field(default_factory=list)
    # 邏輯層：通用屬性 (SAN Cost, Death Condition 等)
    properties: Dict[str, Any] = Field(default_factory=dict)
    # 房間內事件
    events: List[ScriptedEvent] = Field(default_factory=list)
    # "car_4": {
    #       "id": "car_4",
    #       "name": "4號車廂 (乘務員所在)",
    #       "description": "這節車廂內有明顯的混亂痕跡。地上有一道長長的血跡拖曳痕，一直延伸到車廂中央。一名穿著制服的乘務員倒在地上，似乎受了重傷。",
    #       "exits": {
    #         "forward": "car_3",
    #         "backward": "car_5"
    #       },
    #       "items": []
    #     }

# 4. NPC 定義
class NPCDefinition(BaseModel):
    id: str
    name: str
    tags: List[str] = Field(default_factory=list) # RAG 關鍵字
    initial_location: str
    initial_status: str = "normal"
    stats: Dict[str, int] = Field(default_factory=dict) # HP, SAN 等數值
    
    # 以下敘事欄位變為 Optional，因為主要依賴 RAG 的 lore.txt
    description: Optional[str] = None
    personality: Optional[str] = None
    motivation: Optional[str] = None
    dialogue_style: Optional[str] = None
    #   "npcs": [
    #     {
    #       "id": "kyoyama",
    #       "name": "京山 人吉",
    #       "description": "穿著制服的電車乘務員，大約30歲。右腿有嚴重的撕裂傷（咬痕），傷口發紫流血。他處於休克邊緣，臉色慘白，冷汗直流。",
    #       "personality": "膽小、神經質、責任感強、依賴他人。經歷了恐怖襲擊後處於極度驚恐狀態。",
    #       "motivation": "想要活下去，並試圖將電車停下來（他認為停下來才能逃跑，不知道後方有大嘴）。",
    #       "dialogue_style": "說話結巴、語氣充滿恐懼、使用敬語、經常發出疼痛的呻吟。提到怪物時會歇斯底里。",
    #       "initial_location": "car_4",
    #       "initial_status": "injured"
    #     }
    #   ],
# 5. 結局定義
class Ending(BaseModel):
    id: str
    name: str
    condition_desc: str
    description: Optional[str] = None
    type: str
#   "endings": [
#     {
#       "id": "ending_a",
#       "name": "結局 A (True End)",
#       "condition_desc": "玩家在駕駛室將右側控制桿「往下拉」 (加速)，試圖衝破黑暗。",
#       "description": "電車加速到了極致，發出咆哮般的聲響！視野突然被刺眼的白光覆蓋，吞沒了一切恐懼。\n...\n你睜開雙眼，發現自己正坐在明亮的6號車廂裡。廣播傳來：『終點站已到站』。站務人員關切地看著滿身大汗的你。一切彷彿只是一場惡夢，但你活下來了。\n(恭喜生還！SAN 值回復 1d6+2)",
#       "type": "true_end"
#     },

class ScenarioMeta(BaseModel):
    id: str
    title: str
    start_node_id: str

# 6. 劇本定義
class Scenario(BaseModel):
    meta: ScenarioMeta
    # 所有房間節點
    nodes: Dict[str, Room]
    # 物品註冊表 (ID -> ItemDef)
    items: Dict[str, ItemDef] = Field(default_factory=dict)
    npcs: List[NPCDefinition] = Field(default_factory=list)
    global_events: List[ScriptedEvent] = Field(default_factory=list)
    endings: List[Ending] = Field(default_factory=list)
    # 為了方便程式碼存取，提供捷徑 property
    @property
    def start_node_id(self):
        return self.meta.start_node_id
    @property
    def title(self):
        return self.meta.title