import json
from typing import List, Optional
from src.llm.client import llm_client
from src.core.state import NPCState
from src.util.logger import logger
# [修改 1] 重用我們在 Agent 寫好的強韌解析器 (避免重造輪子)
from src.llm.agent import extract_first_json_object 

class NPCEngine:
    def __init__(self):
        logger.log("[NPCEngine.__init__]", "system.txt")

    def react(self, npc: NPCState, player_input: str, environment_desc: str, history: List[str] = []) -> dict:
        """
        讓 NPC 根據玩家行動做出反應
        Args:
            history: 最近的對話紀錄 (從 main.py 傳入 chat_history_buffer)
        """
        logger.log(f"[NPCEngine.react] NPC: {npc.name}", "system.txt")
        
        # 1. 處理對話歷史，讓 NPC 有上下文感
        recent_context = ""
        if history:
            # 取最後 3 句即可，避免 Prompt 太長
            recent_context = "\n[近期對話紀錄]:\n" + "\n".join(history[-3:])

        # 2. 構建 Prompt
        prompt = f"""
你現在正在進行角色扮演 (Roleplay)。請完全沉浸於以下角色，對玩家的行動作出反應。

【NPC 資料】
姓名: {npc.name}
描述: {npc.description or "詳見劇情描述"} 
性格: {npc.personality}
動機: {npc.motivation}
狀態: {npc.status} (位置: {npc.location})
**對玩家好感度**: {npc.relation} (0=仇恨, 50=中立, 100=信賴)
**說話風格**: {npc.dialogue_style}

【當前情境】
{environment_desc}
{recent_context}

【玩家行動】
"{player_input}"

【任務】
請基於 NPC 的性格、當前狀態與好感度，決定反應。
若 NPC 處於昏迷(unconscious)或死亡(dead)狀態，請回傳空字串或省略對話。

請輸出單一 JSON 物件：
{{
    "thought": "簡短思考你的情緒、對玩家的看法、以及下一步打算",
    "dialogue": "你要說的話 (請嚴格遵守說話風格，如口吃、慘叫、冷淡)",
    "action": "描述你的肢體動作 (如發抖、後退、點頭)"
}}

⚠️ 禁止使用 Markdown 標記，直接輸出 JSON 即可。
"""
        
        # 3. 呼叫 LLM
        # 溫度設高一點 (0.7~0.8) 讓 NPC 比較生動
        response = llm_client.chat([{"role": "user", "content": prompt}], temperature=0.75)
        logger.log(f"[NPCEngine.react] Response: {response}", "system.txt")
        
        # 4. 解析結果 (使用強韌解析器)
        try:
            json_str = extract_first_json_object(response)
            if json_str:
                # 容錯處理：修正單引號
                if "'" in json_str and '"' not in json_str:
                    json_str = json_str.replace("'", '"')
                return json.loads(json_str)
            else:
                # 如果解析失敗，回傳原始文字當作對話，動作設為預設
                return {"dialogue": response, "action": "..."}
                
        except Exception as e:
            print(f"⚠️ NPC 解析失敗: {e}")
            return {"dialogue": "......", "action": "沒有反應"}

npc_engine = NPCEngine()