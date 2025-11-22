import json
import re

class IntentAnalyzer:
    def __init__(self, client, model, item_db):
        self.client = client
        self.model = model
        self.item_db = item_db # 必須注入 world_data 中的 item_database

    def analyze(self, player_input, scene_data, player):
        """
        :param player: PlayerManager 的實例 (用來讀取 inventory 和 status)
        """
        
        # 1. 準備 [可用出口]
        exit_options = {
            k: f"{v.get('description','')} (關鍵字:{','.join(v.get('keywords',[]))})" 
            for k, v in scene_data.get("exits", {}).items()
        }
            
        # 2. 準備 [可用物品] (合併 場景物品 + 背包物品)
        item_options = {}
        
        # A. 加入場景物品
        for k, v in scene_data.get("interactables", {}).items():
            item_options[k] = f"[場景] {v.get('description','')} (關鍵字:{','.join(v.get('keywords',[]))})"

        # B. 加入背包物品 (從 ID 查 Name)
        for item_id in player.inventory:
            if item_id in self.item_db:
                item_def = self.item_db[item_id]
                # 顯示名稱作為提示
                item_options[item_id] = f"[背包] {item_def['name']} (描述: {item_def.get('description', '')})"

        # 3. 準備 Prompt
        system_prompt = f"""
        你是一個 TRPG 意圖分析引擎。請根據 [玩家輸入] 與當前狀態進行分類：

        === 當前狀態資料 ===
        [可用出口]: {json.dumps(exit_options, ensure_ascii=False)}
        [可用物品 (含背包)]: {json.dumps(item_options, ensure_ascii=False)}
        
        === 分類規則 (優先級由高至低) ===

        1. QUERY (查詢): 
           - 詢問 **自身狀態** (HP, SAN, MP, 技能數值)。
           - 詢問 **背包內容** (我有什麼, 檢查背包)。
           - 詢問 **位置/環境資訊** (我在哪)。
           - ★ 強制規則：若受詞是「屬性數值」，一律為 QUERY。

        2. MOVE (移動): 
           - 玩家想去某個出口。

        3. INTERACT (互動): 
           - 玩家對 [可用物品] 清單中的目標進行操作。
           - 包含：觀察場景物件、**使用/閱讀背包裡的物品**。
           - ★ 關鍵：必須能對應到 [可用物品] 中的 Key (ID)。
           - 範例："讀報紙" (若報紙在背包) -> INTERACT (target_id: newspaper)。

        4. SKILL (泛用技能): 
           - 使用能力但無特定目標 (觀察周遭, 仔細聽, 潛行, 回想)。

        5. OTHER (其他): 閒聊或無法分類。

        === 輸出格式 (JSON) ===
        {{
            "action": "QUERY" | "MOVE" | "INTERACT" | "SKILL" | "OTHER",
            "target_id": "匹配到的 ID (String)，否則 null",
            "skill_name": "若為 SKILL，填入技能名稱，否則 null",
            "reason": "理由"
        }}
        """

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': player_input}],
                stream=False
            )
            content = response['message']['content']
            match = re.search(r'\{.*\}', content, re.DOTALL)
            return json.loads(match.group(0)) if match else {"action": "OTHER", "reason": "解析失敗"}
        except Exception as e:
            print(f"意圖分析錯誤: {e}")
            return {"action": "OTHER", "reason": "Error"}