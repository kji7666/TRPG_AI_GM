from src.core.tools import UniversalTools
from src.core.state import GameState, PlayerState, PlayerStats, WorldState

p_stats = PlayerStats(HP=13, SAN=45)
player = PlayerState(name="姜敏", stats=p_stats, inventory=["手機"])
world = WorldState()
game = GameState(player=player, world=world)
tools = UniversalTools(game)

print("\n[測試 1] search")
result = tools.search_knowledge("第6車廂") # 模擬 65 技能檢定
print(f"擲骰結果: {result}")