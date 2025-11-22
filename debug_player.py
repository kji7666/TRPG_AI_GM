import json
from player_manager import PlayerManager

# 載入並轉換
p = PlayerManager('player.json')

print(f"玩家名稱: {p.name}")

# 顯示轉換後的技能表 (前 5 個)
print("\n=== 轉換後的技能 (部分) ===")
count = 0
for k, v in p.skills.items():
    print(f"{k}: {v}")
    count += 1
    if count >= 5: break

# 如果你想把轉換後的乾淨資料存成新檔案 (僅供查看，不影響遊戲)
debug_data = {
    "name": p.name,
    "stats": p.stats,
    "skills": p.skills,
    "inventory": p.inventory
}

with open('player_converted_debug.json', 'w', encoding='utf-8') as f:
    json.dump(debug_data, f, ensure_ascii=False, indent=4)
    print("\n[System] 已輸出 debug 檔案: player_converted_debug.json")