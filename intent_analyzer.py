import json
import re

class IntentAnalyzer:
    def __init__(self, client, model):
        self.client = client
        self.model = model

    def analyze(self, player_input, scene_data):
        """
        讓 LLM 分析玩家意圖，並回傳 JSON 格式
        """
        # 1. 準備選項 (選擇題)
        exit_options = {}
        for exit_id, info in scene_data.get("exits", {}).items():
            desc = f"{info.get('description', '前往該區域')} (關鍵字: {', '.join(info.get('keywords', []))})"
            exit_options[exit_id] = desc
            
        item_options = {}
        for item_id, info in scene_data.get("interactables", {}).items():
            desc = f"{info.get('description', '')} (關鍵字: {', '.join(info.get('keywords', []))})"
            item_options[item_id] = desc

        # 2. Prompt
        system_prompt = f"""
        你是一個 TRPG 遊戲的語意分析引擎。
        請分析 [玩家輸入]，並判斷他想與哪個 [可用選項] 互動。

        [可用出口選項 (Exits)]:
        {json.dumps(exit_options, ensure_ascii=False, indent=2)}

        [可用物品選項 (Items)]:
        {json.dumps(item_options, ensure_ascii=False, indent=2)}

        請判斷玩家意圖屬於以下哪一類：
        1. MOVE (移動): 玩家想去某個出口。
        2. INVESTIGATE (調查): 玩家想看/找/使用某個物品。
        3. QUERY (詢問): 玩家詢問位置、自身狀態、時間或環境資訊。
        4. SPEAK (說話): 自言自語或對話。
        5. OTHER (其他): 無法分類。

        請"務必"只回傳一個 JSON 物件，格式如下：
        {{
            "action": "MOVE" 或 "INVESTIGATE" 或 "QUERY" 或 "SPEAK" 或 "OTHER",
            "target_id": "從上面選項的 key 中選出一個最匹配的 ID。若無匹配則填 null",
            "reason": "簡短判斷理由"
        }}
        """

        try:
            response = self.client.chat(
                model=self.model,
                messages=[
                    {'role': 'system', 'content': system_prompt},
                    {'role': 'user', 'content': player_input}
                ],
                stream=False
            )
            
            content = response['message']['content']
            match = re.search(r'\{.*\}', content, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            else:
                return {"action": "OTHER", "target_id": None, "reason": "解析失敗"}

        except Exception as e:
            print(f"意圖分析錯誤: {e}")
            return {"action": "OTHER", "target_id": None, "reason": "發生錯誤"}