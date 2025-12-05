from src.llm.client import llm_client
from src.util.logger import logger

class MemoryManager:
    @staticmethod
    def summarize(current_summary: str, recent_history: list) -> str:
        """
        將「舊的摘要」加上「最近的對話」，壓縮成「新的摘要」
        """
        if not recent_history:
            return current_summary
        logger.log("[MemoryManager.summarize] create prompt", "system.txt")

        # 把對話列表轉成文字
        conversation_text = "\n".join(recent_history)
        
        prompt = f"""
[指令]
你是 TRPG 的紀錄員。請根據以下資訊，更新「劇情摘要」。
請保留重要的關鍵字（如：獲得物品、受傷、重要情報、NPC狀態變化），去除無關緊要的閒聊。

[舊的摘要]
{current_summary}

[最近發生的對話]
{conversation_text}

[任務]
請輸出一段新的、連貫的劇情摘要（包含舊的重點和新的發展）：
"""
        
        # 呼叫 LLM (使用較低的溫度以保持精準)
        new_summary = llm_client.chat([{"role": "user", "content": prompt}], temperature=0.3)
        logger.log("[MemoryManager.summarize] LLM summary", "system.txt")

        return new_summary