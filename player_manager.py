import json
import random

class PlayerManager:
    def __init__(self, filepath='player.json'):
        self.data = self._load_data(filepath)
        self.name = f"{self.data['info']['last_name']}{self.data['info']['first_name']}"
        
        # 建立快速查詢表 (Skill Map)
        # 格式: { "偵查": 65, "聆聽": 20, ... }
        self.skills = self._parse_skills(self.data['skills'])
        
        # 屬性 (STR, DEX...)
        self.stats = {k.upper(): int(v) for k, v in self.data['attr'].items()}
        
        # 背包 (Inventory) - 初始可能為空，或從 extra 解析
        self.inventory = [] 

    def _load_data(self, filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _parse_skills(self, raw_skills_list):
        """將複雜的 skills 陣列攤平成簡單的字典"""
        skill_map = {}
        # player.json 的 skills 是一個二維陣列 (分類 -> 技能列表)
        for category in raw_skills_list:
            for skill in category:
                # 提取技能名稱 (去除 "技艺:", "科学:" 等前綴，方便比對)
                name = skill['name']
                # 提取數值 (value 是成長值? min 是基礎值? 這裡假設 pts 或 min+value 是最終值)
                # 觀察你的 JSON: 'pts' 似乎是最終配點後的數值
                try:
                    score = int(skill.get('pts', skill.get('min', 0)))
                except:
                    score = 0
                
                skill_map[name] = score
                
                # 處理別名 (Alias) 以防萬一
                if "偵查" in name: skill_map["Spot Hidden"] = score
                if "聆聽" in name: skill_map["Listen"] = score
                if "圖書館" in name: skill_map["Library Use"] = score
                if "急救" in name: skill_map["First Aid"] = score
                if "心理學" in name: skill_map["Psychology"] = score
                
        return skill_map

    def get_skill_value(self, skill_name):
        """取得技能數值，若無此技能則回傳基礎值或 0"""
        # 1. 先查屬性 (STR, DEX...)
        if skill_name.upper() in self.stats:
            return self.stats[skill_name.upper()]
            
        # 2. 再查技能
        # 模糊比對
        for name, value in self.skills.items():
            if skill_name in name:
                return value
        
        return 5 # 預設基礎值 (有些技能基礎是 1 或 5)

    def roll_check(self, skill_name, difficulty=None):
        """
        執行檢定
        :param skill_name: 技能名稱 (如 '偵查', 'STR')
        :param difficulty: 目標數值 (若 None 則使用玩家技能值)
        :return: (is_success, roll_result, target_value, desc)
        """
        target = difficulty if difficulty is not None else self.get_skill_value(skill_name)
        roll = random.randint(1, 100)
        
        # COC 7版規則
        if roll == 1:
            result_type = "大成功 (Critical Success)"
            success = True
        elif roll >= 96: # 這裡簡化，正規規則要看技能值是否低於 50
            result_type = "大失敗 (Fumble)"
            success = False
        elif roll <= target // 5:
            result_type = "極限成功 (Extreme Success)"
            success = True
        elif roll <= target // 2:
            result_type = "困難成功 (Hard Success)"
            success = True
        elif roll <= target:
            result_type = "成功 (Success)"
            success = True
        else:
            result_type = "失敗 (Failure)"
            success = False
            
        return {
            "success": success,
            "roll": roll,
            "target": target,
            "result_type": result_type
        }
    
    def update_stat(self, stat_name, amount):
        """更新屬性 (扣血、扣SAN)"""
        stat = stat_name.upper()
        if stat in self.stats:
            self.stats[stat] += amount
            return self.stats[stat]
        return None

# 測試用
if __name__ == "__main__":
    p = PlayerManager()
    print(f"玩家: {p.name}")
    print(f"HP: {p.stats['HP']}")
    print(f"偵查: {p.get_skill_value('偵查')}")
    print(f"檢定結果: {p.roll_check('偵查')}")