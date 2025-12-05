from src.core.state import GameState, PlayerState, PlayerStats, WorldState
from src.core.tools import UniversalTools

print("--- Step 2: 萬能工具測試 ---")

# 1. 初始化一個簡單的狀態
p_stats = PlayerStats(HP=13, SAN=45)
player = PlayerState(name="姜敏", stats=p_stats, inventory=["手機"])
world = WorldState()
game = GameState(player=player, world=world)
tools = UniversalTools(game)

# 2. 測試擲骰子
print("\n[測試 1] 擲骰子")
result = tools.roll_dice("1d100", difficulty=65) # 模擬 65 技能檢定
print(f"擲骰結果: {result}")

# 3. 測試修改 Pydantic 數值 (HP)
print("\n[測試 2] 修改固定屬性 (HP)")
msg = tools.modify_state("player.stats.HP", -2, "add")
print(msg)
assert game.player.stats.HP == 11

# 4. 測試修改/新增 Dict 變數 (World Flags)
print("\n[測試 3] 新增動態世界變數")
msg = tools.modify_state("world.flags.door_broken", True, "set")
print(msg)
assert game.world.flags["door_broken"] == True

# 5. 測試列表操作 (背包)
print("\n[測試 4] 列表操作 (背包)")
# 加鑰匙
print(tools.modify_state("player.inventory", "舊鑰匙", "append"))
# 丟手機
print(tools.modify_state("player.inventory", "手機", "remove"))
print(f"最終背包: {game.player.inventory}")
assert "舊鑰匙" in game.player.inventory
assert "手機" not in game.player.inventory

# 6. 測試深層嵌套 (NPC 狀態)
print("\n[測試 5] 深層路徑自動創建 (模擬 NPC 標記)")
# 即使 world.flags 裡沒有 "kyoyama" 這個 key，setdefault 也應該要能處理 (如果是 dict)
# 但注意：我們在 state.py 定義 npcs 是 Dict[str, NPCState]
# 我們試著修改一個不存在於 flags 裡的深層變數
msg = tools.modify_state("world.flags.event.monster_status", "angry", "set")
print(msg)
print(f"World Flags: {game.world.flags}")