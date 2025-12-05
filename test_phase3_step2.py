from src.scenarios.loader import loader
from src.core.state import GameState, PlayerState, WorldState
from src.core.tools import UniversalTools
from src.core.event_engine import EventEngine

print("--- Phase 3: Step 2 事件引擎測試 ---")

# 1. 初始化
scenario = loader.load("dark_compartment.json")
player = PlayerState(name="測試員")
world = WorldState(current_node_id="car_6") # 初始回合為 0
game = GameState(player=player, world=world, scenario=scenario) 
tools = UniversalTools(game)
engine = EventEngine(game, tools)

# 2. 模擬時間流逝 (Turn 1 ~ 7)
for turn in range(1, 8):
    # 更新回合數
    game.world.turn_count = turn
    print(f"\n🕒 [第 {turn} 回合結束]")
    
    # 觸發事件檢查
    messages = engine.process_events(trigger_type="turn_end")
    
    if messages:
        for msg in messages:
            print(f"📣 系統廣播: {msg}")
            
    # 驗證第 6 回合的 flag 是否被設定
    if turn == 6:
        is_destroyed = game.world.flags.get("car_7_destroyed")
        print(f"   (檢查 flag 'car_7_destroyed': {is_destroyed})")
        assert is_destroyed == True

print("\n測試完成。")