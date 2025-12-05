from src.core.state import NPCState
from src.core.npc_engine import npc_engine

print("--- Phase 4: Step 2 NPC 思考引擎測試 ---")

# 1. 手動建立一個京山 (模擬從劇本讀取後的狀態)
kyoyama = NPCState(
    id="kyoyama",
    name="京山 人吉",
    description="受傷的電車乘務員，腿部流血。",
    personality="膽小、神經質、依賴他人",
    motivation="想活下去，不想被拋下",
    dialogue_style="說話結巴、語氣恐懼、使用敬語、會發出痛呼",
    location="car_4",
    status="injured"
)

# 2. 模擬場景
env_desc = "車廂內燈光閃爍，遠處傳來怪物的低吼聲。空氣中瀰漫著血腥味。"

# 3. 測試情境 A: 玩家友善
player_input_a = "別怕，我會帶你出去的。你的腿還能走嗎？"
print(f"\n[情境 A] 玩家: {player_input_a}")
print("NPC 正在思考...")
response_a = npc_engine.react(kyoyama, player_input_a, env_desc)
print(f"京山: 「{response_a.get('dialogue')}」")
print(f"*動作*: {response_a.get('action')}")

# 4. 測試情境 B: 玩家威脅 (測試性格反應)
player_input_b = "閉嘴！再吵就把你丟在這裡餵怪物！"
print(f"\n[情境 B] 玩家: {player_input_b}")
print("NPC 正在思考...")
response_b = npc_engine.react(kyoyama, player_input_b, env_desc)
print(f"京山: 「{response_b.get('dialogue')}」")
print(f"*動作*: {response_b.get('action')}")