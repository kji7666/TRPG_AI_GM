from src.scenarios.loader import loader

print("--- Phase 3: Step 1 事件模型載入測試 ---")

try:
    scenario = loader.load("dark_compartment.json")
    print(f"✅ 成功載入劇本: {scenario.title}")
    
    print(f"\n[全局事件列表] (共 {len(scenario.global_events)} 個)")
    for event in scenario.global_events:
        print(f"- ID: {event.id}")
        print(f"  名稱: {event.name}")
        print(f"  條件: {event.condition}")
        print(f"  效果: {event.effect_type}")
        print(f"  訊息: {event.message[:30]}...")

except Exception as e:
    print(f"❌ 載入失敗: {e}")