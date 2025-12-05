# src/core/dice.py
import random
import re

class Dice:
    @staticmethod
    def roll(expr: str) -> int:
        """
        解析並執行擲骰，例如 "1d100", "1d6+2"
        """
        # 簡單的正則表達式匹配 XdY(+Z)
        match = re.match(r"(\d+)d(\d+)(?:\+(\d+))?", expr)
        if not match:
            # 如果格式不對，預設回傳 0 或拋出錯誤，這裡簡單處理回傳 0
            return 0
        
        count = int(match.group(1))
        sides = int(match.group(2))
        bonus = int(match.group(3) or 0)
        
        total = sum(random.randint(1, sides) for _ in range(count)) + bonus
        return total

    @staticmethod
    def check(skill_value: int) -> dict:
        """
        進行 COC 7版 的檢定
        回傳: {"result": "success/failure/...", "roll": 45}
        """
        roll_val = random.randint(1, 100)
        
        if roll_val == 1:
            status = "critical_success" # 大成功
        elif roll_val == 100:
            status = "fumble" # 大失敗
        elif roll_val <= skill_value // 5:
            status = "extreme_success" # 極難成功
        elif roll_val <= skill_value // 2:
            status = "hard_success" # 困難成功
        elif roll_val <= skill_value:
            status = "regular_success" # 普通成功
        else:
            status = "failure" # 失敗
            
        return {"status": status, "roll": roll_val}