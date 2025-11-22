import json
import random
import os

class GameEngine:
    def __init__(self, world_data, player):
        self.world_data = world_data
        self.player = player
        
        # 初始化狀態
        self.current_scene_id = world_data["initial_scene"]
        self.flags = world_data["global_vars"]["flags"]
        self.item_db = world_data.get("item_database", {})
        
        self.skill_map = self._load_skill_map('skill_map.json')

    def _load_skill_map(self, filepath):
        """讀取技能映射檔，若不存在則使用最小預設值"""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[警告] 找不到 {filepath}，使用預設技能表。")
            return {
                "偵查": "Spot Hidden", "觀察": "Spot Hidden",
                "聆聽": "Listen", "聽": "Listen"
            }
        
    def get_current_scene(self):
        return self.world_data["scenes"][self.current_scene_id]

    def get_setting(self):
        return self.world_data.get("setting", {})

    def get_full_description(self, scene=None):
        """處理動態描述 (Overlay)"""
        if scene is None:
            scene = self.get_current_scene()
            
        desc = scene['base_description']
        if "overlays" in scene:
            for overlay in scene["overlays"]:
                cond = overlay["condition"]
                is_met = False
                
                if ">" in cond:
                    k, v = cond.split(">")
                    # 讀取 world_data 中的 global_vars (如 turn_count)
                    actual_val = self.world_data["global_vars"].get(k.strip(), 0)
                    if actual_val > int(v): is_met = True
                elif "==" in cond:
                    k, v = cond.split("==")
                    expected = v.strip().lower() == "true"
                    if self.flags.get(k.strip()) == expected: is_met = True
                
                if is_met: desc += f" {overlay['text']}"
        return desc

    def process_intent(self, intent):
        """主邏輯分流"""
        action = intent["action"]
        scene = self.get_current_scene()
        
        if action == "QUERY":
            return self._handle_query(intent, scene)
        elif action == "MOVE":
            return self._handle_move(intent, scene)
        elif action == "SKILL":
            return self._handle_skill(intent, scene)
        elif action == "INTERACT":
            return self._handle_interact(intent, scene)
        else:
            return f"其他行動：{intent.get('reason')}"

    # === 內部處理函式 ===

    def _execute_actions(self, action_list):
        results = []
        for act in action_list:
            atype = act.get("type")
            
            if atype == "narrate":
                results.append(act["content"])
                
            elif atype == "add_item":
                item_id = act["id"]
                if item_id in self.item_db:
                    if self.player.add_item_to_inventory(item_id):
                        results.append(f"【獲得物品】：{self.item_db[item_id]['name']}")
                    else:
                        results.append("（已持有）")
                        
            elif atype == "set_flag":
                self.flags[act["key"]] = act["val"]
                
            elif atype == "modify_stat":
                # ★ 修正重點：真正呼叫 player 來更新數值 ★
                target = act["target"] # e.g., "SAN", "HP"
                val_str = str(act["val"]) # e.g., "-1", "-1d6"
                
                # 這裡簡單處理固定數值，若要支援骰子字串需寫 parser
                # 為了 MVP，我們先假設 JSON 裡寫的是數字字串 "-1"
                try:
                    amount = int(val_str)
                    new_val = self.player.update_stat(target, amount)
                    results.append(f"【狀態變更】：{target} {amount} (當前: {new_val})")
                except ValueError:
                    results.append(f"[系統錯誤] 無法解析數值變更: {val_str}")

        return " ".join(results)

    def _handle_query(self, intent, scene):
        reason = intent.get("reason", "").lower()
        
        # 1. 背包查詢
        if "背包" in reason or "持有" in reason or "inventory" in reason:
            if not self.player.inventory: return "玩家查詢背包。系統：背包是空的。"
            names = [self.item_db[iid]["name"] for iid in self.player.inventory if iid in self.item_db]
            return f"玩家查詢背包。目前持有：{'、'.join(names)}。"
            
        # 2. 數值查詢
        if "hp" in reason or "血" in reason:
            return f"玩家查詢狀態。HP: {self.player.stats.get('HP')}"
        if "san" in reason or "理智" in reason:
            return f"玩家查詢狀態。SAN: {self.player.stats.get('SAN')}"
            
        return f"玩家詢問資訊。位置：{self.current_scene_id}。場景：{self.get_full_description(scene)}"

    def _handle_move(self, intent, scene):
        target = intent.get("target_id")
        if target and target in scene["exits"]:
            exit_info = scene["exits"][target]
            if exit_info.get("locked", False):
                return f"移動失敗。通往 {target} 的門鎖住了。"
                
            self.current_scene_id = target
            return f"移動成功。玩家進入了 {target}。"
        return "移動失敗。無路可走。"

    def _handle_skill(self, intent, scene):
        raw_skill = intent.get("skill_name", "")
        skill_key = "Spot Hidden" # 預設
        for k, v in self.skill_map.items():
            if k in raw_skill: skill_key = v; break
        
        res = self.player.roll_check(skill_key)
        msg = f"玩家進行【{skill_key}】檢定。{res['msg']}。"
        
        if res["success"]:
            hint = scene.get("scene_hints", {}).get(skill_key, "你感覺有些不對勁。")
            msg += f" 發現線索：{hint}"
        else:
            msg += " 什麼也沒發現。"
        return msg

    def _handle_interact(self, intent, scene):
        target = intent.get("target_id")
        scene_items = scene.get("interactables", {})
        
        # ★ 修正重點：搜尋順序 (場景 -> 背包) ★
        
        # 1. 搜尋場景物品
        if target in scene_items:
            item = scene_items[target]
            itype = item.get("type", "read")
            
            # 處理 NPC (簡單版)
            if itype == "npc":
                return f"玩家與 NPC {item.get('name')} 進行了互動。描述：{item.get('description')}"

            # 處理檢定類互動
            if itype == "check":
                skill = item.get("skill", "Spot Hidden")
                diff = item.get("difficulty", 50)
                res = self.player.roll_check(skill, diff)
                
                actions = item.get("on_success", []) if res["success"] else item.get("on_fail", [])
                exec_res = self._execute_actions(actions)
                return f"互動 {target}。{res['msg']}。結果：{exec_res}"
            
            # 處理閱讀/觀察類
            elif itype == "read":
                return f"閱讀/觀察 {target}。內容：{item.get('content', item.get('description'))}"
        
        # 2. 搜尋背包物品 (如果場景裡沒有，但背包有)
        elif target in self.player.inventory:
            # 從 item_database 獲取資料
            if target in self.item_db:
                item_def = self.item_db[target]
                return f"玩家檢查背包中的【{item_def['name']}】。描述：{item_def['description']}"
        
        return "互動失敗。找不到目標 (不在場景也不在背包中)。"