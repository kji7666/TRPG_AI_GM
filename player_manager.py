import json
import random
import os

class PlayerManager:
    def __init__(self, filepath='player.json'):
        self.filepath = filepath
        self.data = self._load_data(filepath)
        
        # 1. 基礎資訊解析
        info = self.data.get("info", {})
        self.name = f"{info.get('last_name', '')}{info.get('first_name', '')}"
        
        # 2. 屬性解析 (將字串轉為整數)
        self.stats = self._parse_attributes(self.data.get("attr", {}))
        
        # 3. 技能解析 (攤平 + 中英映射)
        self.skills = self._parse_skills(self.data.get("skills", []))
        
        # 4. 背包系統 (如果 JSON 裡沒有 inventory 欄位，就初始化為空)
        if "inventory" not in self.data:
            self.data["inventory"] = []
        self.inventory = self.data["inventory"]

    def _load_data(self, filepath):
        if not os.path.exists(filepath):
            print(f"[警告] 找不到 {filepath}，將使用空白角色卡")
            return {"info": {}, "attr": {}, "skills": [], "inventory": []}
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _parse_attributes(self, raw_attr):
        """將屬性轉為大寫 Key 並確保是整數"""
        clean_stats = {}
        for k, v in raw_attr.items():
            try:
                clean_stats[k.upper()] = int(v)
            except (ValueError, TypeError):
                clean_stats[k.upper()] = 0
        return clean_stats

    def _parse_skills(self, raw_skills_list):
        """
        將複雜的二維陣列技能轉為簡單的字典 {SkillName: Value}
        同時處理 簡體/繁體 -> 英文 Key 的映射
        """
        skill_map = {}
        
        # 遍歷二維陣列
        for category in raw_skills_list:
            for skill in category:
                name = skill.get('name', '')
                # 數值提取邏輯：有些生成器用 pts，有些用 value 或 min
                # 這裡假設 pts 是最終配點值，若無則回退到 min
                try:
                    val = int(skill.get('pts', skill.get('value', skill.get('min', 0))))
                except:
                    val = 5
                
                skill_map[name] = val

        # === 關鍵：建立別名映射 (Alias Mapping) ===
        # 這樣無論是 "偵查"、"侦查" 還是 "Spot Hidden" 都能查到數值
        aliases = {
            "Spot Hidden": ["侦查", "偵查", "观察", "觀察", "找"],
            "Listen": ["聆听", "聆聽", "听", "聽"],
            "Library Use": ["图书馆", "圖書館", "图书馆使用", "阅读", "閱讀"],
            "Idea": ["灵感", "靈感", "智力", "INT"],
            "Psychology": ["心理学", "心理學"],
            "First Aid": ["急救"],
            "Occult": ["神秘学", "神秘學"],
            "Stealth": ["潜行", "潛行", "隐然", "躲藏"],
            "Track": ["追踪", "追蹤"],
            "Climb": ["攀爬"],
            "Jump": ["跳跃", "跳躍"],
            "Dodge": ["闪避", "閃避"],
            "Persuade": ["说服", "說服"],
            "Fast Talk": ["话术", "話術"],
            "Charm": ["魅惑"],
            "STR": ["力量"],
            "DEX": ["敏捷"],
            "POW": ["意志"],
            "CON": ["体质", "體質"],
            "APP": ["外貌"],
            "EDU": ["教育"],
            "LUCK": ["幸运", "幸運"]
        }

        final_skills = skill_map.copy()
        
        # 將中文技能值同步給英文 Key
        for en_key, cn_keys in aliases.items():
            # 1. 先找中文名對應的數值
            score = 0
            for cn in cn_keys:
                if cn in skill_map:
                    score = max(score, skill_map[cn])
            
            # 2. 如果沒找到技能，嘗試找屬性 (如 STR, DEX)
            if score == 0 and en_key in self.stats:
                score = self.stats[en_key]

            # 3. 如果還是 0，給個基礎值 (視規則而定，這裡簡化為 15 或 5)
            if score == 0:
                score = 15 # 基礎值
            
            final_skills[en_key] = score

        return final_skills

    # ================= 對外 API =================

    def get_value(self, target):
        """取得任意技能或屬性的數值 (支援模糊搜尋)"""
        # 1. 直接查英文 Key
        if target in self.skills:
            return self.skills[target]
        if target.upper() in self.stats:
            return self.stats[target.upper()]
            
        # 2. 模糊比對
        for k, v in self.skills.items():
            if target in k:
                return v
        return 5 # 預設值

    def roll_check(self, target_name, difficulty=None):
        """擲骰檢定"""
        val = self.get_value(target_name)
        target = difficulty if difficulty is not None else val
        
        roll = random.randint(1, 100)
        
        # CoC 7版 規則判斷
        result_type = "失敗"
        success = False
        
        if roll == 1:
            result_type = "大成功"
            success = True
        elif roll >= 96 and val < 50: # 簡化規則
            result_type = "大失敗"
            success = False
        elif roll <= val // 5:
            result_type = "極限成功"
            success = True
        elif roll <= val // 2:
            result_type = "困難成功"
            success = True
        elif roll <= val:
            result_type = "成功"
            success = True
        
        return {
            "success": success,
            "result_type": result_type,
            "roll": roll,
            "target": target,
            "msg": f"(檢定【{target_name}】: {roll}/{target} -> {result_type})"
        }

    def add_item_to_inventory(self, item_id):
        """獲得物品"""
        if item_id not in self.inventory:
            self.inventory.append(item_id)
            self.save_data() # 自動存檔
            return True
        return False

    def has_item(self, item_id):
        return item_id in self.inventory

    def update_stat(self, stat, amount):
        """更新數值 (HP/SAN/MP)"""
        key = stat.upper()
        if key in self.stats:
            self.stats[key] += int(amount)
            # 同步回原始 data 以便存檔
            self.data["attr"][key.lower()] = str(self.stats[key])
            self.save_data()
            return self.stats[key]
        return None

    def save_data(self):
        """將變更寫回 JSON 檔案"""
        # 更新背包
        self.data["inventory"] = self.inventory
        
        with open(self.filepath, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)
        # print("[System] Character saved.")

# 測試用
if __name__ == "__main__":
    p = PlayerManager()
    print(f"載入角色: {p.name}")
    print(f"HP: {p.stats.get('HP')}")
    print(f"偵查(Spot Hidden): {p.get_value('Spot Hidden')}")
    print(f"測試擲骰: {p.roll_check('Spot Hidden')}")