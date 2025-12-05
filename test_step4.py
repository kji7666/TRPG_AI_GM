from src.core.state import GameState, PlayerState, PlayerStats, WorldState
from src.core.tools import UniversalTools
from src.llm.agent import ReActAgent

# 1. 初始化遊戲環境
# 模擬姜敏 (STR 15, HP 13)
p_stats = PlayerStats(STR=15, HP=13, SAN=45)
player = PlayerState(name="姜敏", stats=p_stats, inventory=["手機"])
world = WorldState()
game = GameState(player=player, world=world)

# 2. 啟動工具與 Agent
tools = UniversalTools(game)
agent = ReActAgent(tools, max_steps=5)

print("--- Step 4: ReAct Agent 整合測試 ---")
print(f"初始狀態: HP={game.player.stats.HP}, 背包={game.player.inventory}")

# 3. 發送測試指令
# 這個指令很複雜，強迫 AI 必須：
# (1) 判斷這是危險動作 -> (2) 擲骰子 -> (3) 根據骰子結果扣血 -> (4) 描述結果
user_input = "我試圖用頭去撞牆壁，看能不能撞破。"

print(f"\n[Player]: {user_input}")
response = agent.step(user_input)

print(f"\n[KP]: {response}")

print("\n--- 驗證數據變化 ---")
print(f"最終狀態: HP={game.player.stats.HP} (應該要減少)")