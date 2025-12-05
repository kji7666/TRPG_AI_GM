import random
import re
from typing import Any, Dict, Optional, Union
from ..rag.retriever import RAGRetriever 
from src.util.logger import logger

class UniversalTools:
    def __init__(self, game_state):
        logger.log("[UniversalTools.__init__] game, retriever", "system.txt")
        self.game = game_state 
        try:
            self.retriever = RAGRetriever()
        except:
            print("⚠️ 警告: RAG 資料庫未初始化，搜尋功能將無法使用。")
            self.retriever = None

    def roll_dice(self, expression: str = "1d100", difficulty: Optional[Union[int, str]] = None, reason: str = "通用") -> Dict[str, Any]:
        """
        [工具] 執行擲骰
        """
        # 1. 解析骰子表達式
        match = re.match(r"(\d+)d(\d+)(?:\+?(-?\d+))?", str(expression))
        if match:
            count, sides, bonus = int(match.group(1)), int(match.group(2)), int(match.group(3) or 0)
        else:
            count, sides, bonus = 1, 100, 0

        # 2. 執行擲骰
        total = sum(random.randint(1, sides) for _ in range(count)) + bonus
        
        result = {
            "reason": str(reason), # 強制轉字串，防止 AI 傳奇怪的東西
            "expression": expression,
            "total": total,
            "details": f"Rolled {count}d{sides}+{bonus}"
        }

        # 3. [修正] 處理難度判定 (防禦性編程)
        if difficulty is not None:
            try:
                # [關鍵修正] 無論 AI 傳 "57" 還是 57，通通轉成 int
                target = int(difficulty)
                
                if total == 1: status = "critical_success"
                elif total == 100: status = "fumble"
                elif total <= target // 5: status = "extreme_success"
                elif total <= target // 2: status = "hard_success"
                elif total <= target: status = "success"
                else: status = "failure"
                
                result["success_status"] = status
                result["target_difficulty"] = target
                
            except ValueError:
                # 如果 AI 傳了 "unknown" 這種無法轉數字的字串
                result["error"] = f"Invalid difficulty value: {difficulty}"

        # 記錄 Log
        logger.log(f"[Dice] {reason}: {result}", "system.log")
        return result

    def modify_state(self, path: Union[str, list], value: Any, operation: str = "set") -> str:
        """
        [萬能工具] 修改遊戲狀態 (終極防呆版)
        """
        # 1. 容錯處理：如果 AI 傳入 list 類型的路徑 (如 ['player', 'hp'])
        if isinstance(path, list):
            path = ".".join(str(p) for p in path)
        
        # 2. 容錯處理：路徑別名修正
        path_lower = path.lower()
        if path_lower.startswith("player.hp"): path = path.replace("player.hp", "player.stats.HP").replace("player.HP", "player.stats.HP")
        elif path_lower.startswith("player.san"): path = path.replace("player.san", "player.stats.SAN").replace("player.SAN", "player.stats.SAN")
        elif path_lower == "world.location": path = "world.current_node_id"

        # =================================================================
        # [新增] 移動合法性檢查 (含自動 ID 修正)
        # =================================================================
        if "current_node_id" in path or "location" in path_lower:
            current_id = self.game.world.current_node_id
            target_id = value
            
            # 如果原地不動
            if current_id == target_id:
                pass
            
            elif self.game.scenario:
                current_room = self.game.scenario.nodes.get(current_id)
                
                if current_room:
                    # 1. 收集所有合法的出口 ID
                    valid_exits = []
                    for exit_data in current_room.exits.values():
                        if hasattr(exit_data, 'target_node'):
                            if not exit_data.locked: # 這裡先只放沒鎖的，或者讓後面邏輯處理鎖
                                valid_exits.append(exit_data.target_node)
                        else:
                            valid_exits.append(exit_data)
                    
                    # 2. [核心修正] 嘗試自動將「中文名稱」轉換為「ID」
                    # 如果 target_id (例如 "5號車廂") 不在 valid_exits (例如 ["car_5"]) 裡
                    if target_id not in valid_exits:
                        corrected_id = None
                        # 遍歷所有合法出口，檢查名稱是否匹配
                        for exit_id in valid_exits:
                            node = self.game.scenario.nodes.get(exit_id)
                            # 如果名稱完全一樣，或者包含關係 (例如 AI 寫 "前往5號車廂")
                            if node and (target_id == node.name or target_id in node.name or node.name in target_id):
                                corrected_id = exit_id
                                break
                        
                        # 如果找到了對應的 ID，就自動修正
                        if corrected_id:
                            print(f"  🔧 [System] 自動修正移動目標: '{target_id}' -> '{corrected_id}'")
                            target_id = corrected_id
                            value = corrected_id # 更新要寫入的值
                        else:
                            # 真的找不到，才報錯
                            return f"❌ 移動失敗：無法從 {current_id} 前往 '{target_id}'。請確認路徑是否存在。"

                    # 3. 二次檢查 (針對鎖的邏輯)
                    # 如果修正後是合法的 ID，再檢查一次是不是鎖著的 (針對 ComplexExit)
                    # (這段邏輯可以根據你的 ComplexExit 結構微調，這裡做個簡單檢查)
                    for exit_data in current_room.exits.values():
                        if hasattr(exit_data, 'target_node') and exit_data.target_node == target_id:
                            if exit_data.locked:
                                return f"❌ 移動失敗：通往 {target_id} 的門是鎖著的。"

        # =================================================================

        keys = path.split('.')
        current_obj = self.game
        
        try:
            # --- 導航到目標物件 ---
            for key in keys[:-1]:
                if isinstance(current_obj, dict):
                    current_obj = current_obj.setdefault(key, {})
                elif hasattr(current_obj, key):
                    current_obj = getattr(current_obj, key)
                else:
                    return f"❌ 路徑錯誤: 找不到 {key} (在 {path} 中)"

            target_key = keys[-1]

            # 取得當前值
            current_val = None
            is_dict = isinstance(current_obj, dict)
            
            if is_dict:
                current_val = current_obj.get(target_key)
            elif hasattr(current_obj, target_key):
                current_val = getattr(current_obj, target_key)

            # --- 執行操作 ---
            
            if operation == "set":
                if is_dict: 
                    current_obj[target_key] = value
                else: 
                    setattr(current_obj, target_key, value)
                # 使用 f-string 避免 "str" + int 錯誤
                return f"✅ 已設定 {path} = {value}"

            elif operation == "add":
                # --- 強制轉型邏輯 (解決你的報錯核心) ---
                try:
                    # 處理 Current Value
                    num_current = 0
                    if current_val is not None:
                        # 如果是字串，嘗試轉換
                        str_val = str(current_val)
                        if "." in str_val: num_current = float(str_val)
                        else: num_current = int(str_val)
                    
                    # 處理 Input Value
                    str_input = str(value)
                    if "." in str_input: num_value = float(str_input)
                    else: num_value = int(str_input)

                    # 計算
                    new_val = num_current + num_value
                    
                    # 保持整數潔癖
                    if isinstance(new_val, float) and new_val.is_integer():
                        new_val = int(new_val)

                except ValueError:
                    return f"❌ 運算失敗: 無法將 '{current_val}' 或 '{value}' 轉為數字進行加減。"

                # 寫回
                if is_dict: current_obj[target_key] = new_val
                else: setattr(current_obj, target_key, new_val)
                
                return f"✅ {path} 變更了 {value} (當前: {new_val})"

            elif operation == "append":
                if current_val is None: current_val = []
                if not isinstance(current_val, list): current_val = []
                
                current_val.append(value)
                if is_dict: current_obj[target_key] = current_val # 確保寫回
                return f"✅ 已將 [{value}] 加入 {path}"

            elif operation == "remove":
                if not isinstance(current_val, list):
                    return f"❌ 錯誤: {path} 不是列表"
                
                if value in current_val:
                    current_val.remove(value)
                    return f"✅ 已將 [{value}] 從 {path} 移除"
                else:
                    return f"⚠️ 警告: {path} 裡面沒有 [{value}]"
            
            else:
                return f"❌ 未知操作: {operation}"

        except Exception as e:
            return f"❌ 系統錯誤: {str(e)}"
        

    def search_knowledge(self, query: str) -> str:
        """
        [工具] 查詢規則書或劇本設定
        Args:
            query: 關鍵字或問題 (例如 "循聲者弱點", "SAN值歸零後果")
        """
        logger.log("[UniversalTools.search_knowledge] rag search : " + query, "system.txt")
        if not self.retriever:
            return "錯誤：知識庫離線中。"
        

        logger.log(f"  🔍 [RAG] 正在檢索: {query}", "think.txt")
        result = self.retriever.query(query)
        logger.log("[UniversalTools.search_knowledge] result" + result, "system.txt")
        return result