from src.scenarios.loader import loader
from src.core.state import NPCState

print("--- Phase 4: Step 1 NPC 模型測試 ---")

# 1. 載入劇本
try:
    scenario = loader.load("dark_compartment.json")
    print(f"✅ 劇本載入成功，發現 {len(scenario.npcs)} 個 NPC 設定。")
except Exception as e:
    print(f"❌ 載入失敗: {e}")
    exit()

# 2. 檢查數據
npc_def = scenario.npcs[0]
print(f"\n[NPC 設定檔]")
print(f"姓名: {npc_def.name}")
print(f"性格: {npc_def.personality}")
print(f"說話: {npc_def.dialogue_style}")

# 3. 模擬轉換為運行狀態 (Runtime State)
kyoyama_state = NPCState(
    id=npc_def.id,
    name=npc_def.name,
    description=npc_def.description,
    personality=npc_def.personality,
    motivation=npc_def.motivation,
    dialogue_style=npc_def.dialogue_style,
    location=npc_def.initial_location,
    status=npc_def.initial_status
)

print(f"\n[NPC 運行狀態建立成功]")
print(f"當前位置: {kyoyama_state.location}")
print(f"狀態: {kyoyama_state.status}")
print(f"關係值: {kyoyama_state.relation}")