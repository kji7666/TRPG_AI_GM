import json
import os
from src.core.state import GameState, PlayerState, WorldState

print("--- Step 1: 複雜數據結構載入測試 ---")

# 1. 讀取你的真實角色卡
player_file = "data/players/player.json"

if not os.path.exists(player_file):
    print(f"❌ 找不到 {player_file}，請先建立檔案！")
    exit()

with open(player_file, "r", encoding="utf-8") as f:
    raw_data = json.load(f)

print(f"檔案讀取成功，正在解析 {raw_data.get('name')} 的數據...")

# 2. 轉換為 Pydantic 模型
try:
    # 直接將 JSON 灌入 PlayerState
    # Pydantic 會自動把 "stats" 裡的 STR, CON 填入 PlayerStats
    # 把 "skills" 裡的那堆技能填入 skills Dict
    player = PlayerState(**raw_data)
    
    print("✅ Pydantic 解析成功！")
    print(f"角色: {player.name}")
    print(f"STR: {player.stats.STR} (來自 stats 物件)")
    print(f"HP: {player.stats.HP}")
    print(f"技能數量: {len(player.skills)} 個")
    print(f"偵查技能: {player.skills.get('偵查')} (應為 65)")
    print(f"Spot Hidden: {player.skills.get('Spot Hidden')} (應為 65)")
    
except Exception as e:
    print(f"❌ 解析失敗: {e}")
    exit()

# 3. 初始化世界並組裝 GameState
world = WorldState()
game = GameState(player=player, world=world)

# 4. 模擬 AI 使用 (壓力測試)
print("\n[壓力測試] 模擬 AI 讀取與修改...")
# 假設 AI 要進行 "考古學" 檢定
skill_name = "考古學"
skill_val = game.player.skills.get(skill_name, 5) # 預設值 5
print(f"AI 查詢 '{skill_name}': {skill_val}")

# 假設 AI 造成玩家 1d3 傷害
game.player.stats.HP -= 2
print(f"AI 修改 HP -> {game.player.stats.HP}")

print("\n測試完成。結構足以應付複雜角色卡。")