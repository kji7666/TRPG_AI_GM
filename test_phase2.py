from src.core.state import GameState, PlayerState, PlayerStats, WorldState
from src.core.tools import UniversalTools
from src.llm.agent import ReActAgent

print("--- Phase 2: Agent + RAG 整合測試 ---")

# 1. 初始化
p_stats = PlayerStats(HP=10, SAN=50)
player = PlayerState(name="測試員", stats=p_stats)
world = WorldState()
game = GameState(player=player, world=world)

tools = UniversalTools(game)
agent = ReActAgent(tools, max_steps=5)

# 2. 測試問題：這是一個劇本裡的隱藏設定，AI 不查資料絕對不知道
user_input = "我好像聽到怪物在叫，我想知道這種怪物有什麼弱點？"

print(f"\n[Player]: {user_input}")
response = agent.step(user_input)

print(f"\n[KP]: {response}")