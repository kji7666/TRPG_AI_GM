import json
import re
from typing import Optional
from .client import llm_client
from .prompts import SystemPromptBuilder
from ..core.tools import UniversalTools
from src.util.logger import logger

def extract_first_json_object(text: str) -> Optional[str]:
    """
    從文字中提取第一個完整的 JSON 物件。
    """
    # stack 括號平衡法
    stack = 0
    start_index = -1
    found_start = False
    
    for i, char in enumerate(text):
        if char == '{': # 第一個 {
            if not found_start:
                start_index = i
                found_start = True
            stack += 1
        elif char == '}':
            if found_start:
                stack -= 1
                if stack == 0:
                    # 最尾的 }
                    return text[start_index : i+1]
    
    return None

class ReActAgent:
    def __init__(self, tools: UniversalTools, max_steps: int = 10):
        logger.log("ReActAgent.__init__] tools, system_prompt", "system.txt")
        self.tools = tools
        self.max_steps = max_steps
        self.system_prompt = SystemPromptBuilder.get_prompt() # 存著每次加

    def step(self, user_input: str, summary: str = "", recent_history: list = None) -> str:
        if recent_history is None:
            recent_history = []
            
        logger.log("[ReActAgent.step] prompt 整理 : GameState, history", "system.txt")
        # 1. 準備 Context
        game_state_json = self.tools.game.to_json()
        
        # 將 list 轉為 str 傳給 Prompt
        history_str = "\n".join(recent_history)
        
        user_prompt = SystemPromptBuilder.get_user_prompt(
            game_state_json, 
            user_input, 
            summary, 
            history_str
        )

        # prompt setting
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        logger.log(f"\n🔵 [Agent] 收到指令: {user_input}", "think.txt")
        
        # 進入思考迴圈
        logger.log("[ReActAgent.step] ReAct loop start", "system.txt")
        for i in range(self.max_steps):
            logger.log(f"  🔄 Step {i+1} (思考中...)", "think.txt")
            
            # prompt 給 LLM
            logger.log("[ReActAgent.step] prompt 給 LLM", "system.txt")
            response = llm_client.chat(messages, temperature=0.4)
            logger.log("[ReActAgent.step] response :\n" + response + "\n", "system.txt")
            # [Debug] 印出raw response，方便除錯
            logger.log(f"\n{'='*20} RAW RESPONSE {'='*20}", "think.txt")
            logger.log(f"{response}", "think.txt")
            logger.log(f"{'='*54}", "think.txt")

            if not response or not response.strip():
                logger.log("⚠️ 模型回傳了空字串，正在重試...", "think.txt")
                continue

            # 將 AI 的思考加入歷史
            messages.append({"role": "assistant", "content": response})
            logger.log("[ReActAgent.step] append response to prompt", "system.txt")
            # response 格式
            # 好的，我正在分析你的狀態...
            # {
            # "action": "roll_dice",
            # "params": {
            #     "expression": "1d100",
            #     "difficulty": 60
            # }
            # }
            # 如果骰失敗，你可能會遇到危險。

            # 要抽出 json
            action_json_str = extract_first_json_object(response)

            # json 內是 LLM 想調用的 tool
            if action_json_str:
                try:
                    # 修復常見的單引號 JSON 錯誤
                    # LLM 很常回：{'tool': 'roll_dice', 'params': {'expression': '1d100'}}, 但 json 是 ""
                    if "'" in action_json_str and '"' not in action_json_str:
                        action_json_str = action_json_str.replace("'", '"')
                        
                    action_data = json.loads(action_json_str) # json to dict
                    # 回應格式 : {"tool": "search_knowledge", "params": {"query": "..."}}
                    tool_name = action_data.get("tool")
                    params = action_data.get("params", {}) # param dict
                    logger.log(f"  🛠️ [Action] 呼叫工具: {tool_name}", "think.txt")
                    logger.log(f"     參數: {params}", "think.txt")

                    # 路由工具
                    logger.log("[ReActAgent.step] use tool " + tool_name + " by response", "system.txt")
                    if tool_name == "modify_state":
                        result = self.tools.modify_state(**params)
                    elif tool_name == "roll_dice":
                        result = self.tools.roll_dice(**params)
                    elif tool_name == "search_knowledge":
                        result = self.tools.search_knowledge(**params)
                    else:
                        result = f"Error: Unknown tool '{tool_name}'"
                    logger.log(f"  👀 [Observation] {result}", "think.txt")

                    # 將結果餵回給 LLM，並強制進入下一次迴圈
                    logger.log("[ReActAgent.step] " + tool_name + " 執行結果 append 到 prompt", "system.txt")
                    messages.append({"role": "user", "content": f"Observation: {str(result)}"})
                    continue

                except json.JSONDecodeError as e: # error 都要 retry
                    print(f"  ❌ JSON 解析失敗: {e}")
                    messages.append({"role": "user", "content": "System Error: Invalid JSON format. Please check your syntax."})
                    continue
                except Exception as e:
                    print(f"  ❌ 執行錯誤: {e}")
                    messages.append({"role": "user", "content": f"System Error: {str(e)}"})
                    continue

            
            # 1. 如果有明確的 Final Answer 標籤 (system prompt有講)
            if "Final Answer:" in response:
                logger.log("[ReActAgent.step] ReAct 結束", "system.txt")
                final_narrative = response.split("Final Answer:")[-1].strip()
                if final_narrative:
                    logger.log(f"\n🟢 [Agent] 思考結束 (Final Answer)", "think.txt")
                    return final_narrative
            
            # 2. 如果沒有 Action 也沒有 Final Answer 標籤
            # 有時候 AI 會忘記寫 Final Answer: 這個關鍵字，直接就把劇情吐出來了
            # 只要 ai 沒打算呼叫工具 (Action)，那我就當作他說的話就是最終結果。
            if not action_json_str:
                logger.log("[ReActAgent.step] ReAct 結束", "system.txt")
                logger.log(f"\n🟢 [Agent] 思考結束 (Final Answer)", "think.txt")
                return response

        return "(系統 : Agent 思考次數過多，已被強制中止。）"