import os
import json
from dotenv import load_dotenv
from ollama import Client

# 匯入自定義模組
from intent_analyzer import IntentAnalyzer
from player_manager import PlayerManager
from game_engine import GameEngine
from narrator import Narrator

def main():
    # 1. 初始化環境與 API 設定
    load_dotenv()
    api_key = os.getenv("LLM_API_KEY")
    host = os.getenv("API_HOST")
    model = os.getenv("MODEL_NAME")

    print("=== COC Agent vFinal (Refactored & Fixed) ===")
    print("正在初始化系統...")

    # 2. 建立 LLM Client
    client = Client(host=host, headers={'Authorization': f'Bearer {api_key}'})
    
    # 3. 載入劇本資料 (World Data)
    try:
        with open('world_data.json', 'r', encoding='utf-8') as f:
            world_data = json.load(f)
            
        # ★ 修正重點 1：提取物品資料庫 (給 IntentAnalyzer 用)
        item_db = world_data.get("item_database", {})
            
    except FileNotFoundError:
        print("錯誤：找不到 world_data.json，請確認檔案是否存在。")
        return

    # 4. 實例化核心模組
    player = PlayerManager('player.json')
    
    # ★ 修正重點 2：將 item_db 傳入分析器
    analyzer = IntentAnalyzer(client, model, item_db)
    
    engine = GameEngine(world_data, player) # 規則引擎接管一切邏輯
    narrator = Narrator(client, model)      # 敘事者接管 GM 發言

    # 5. 遊戲開始：顯示初始狀態
    print(f"玩家: {player.name} | HP: {player.stats.get('HP')} | SAN: {player.stats.get('SAN')}")
    
    # 獲取初始場景描述
    start_scene = engine.get_current_scene()
    start_desc = engine.get_full_description(start_scene)
    print(f"\nGM: {start_desc}")

    # 6. 進入主迴圈 (Game Loop)
    while True:
        try:
            player_input = input("\n你: ").strip()
        except EOFError:
            break # 防止 Docker 環境下的輸入錯誤

        if player_input.lower() in ['q', 'exit', 'quit']:
            # 離開時自動存檔
            player.save_data()
            print("遊戲進度已儲存。遊戲結束。")
            break
        
        # A. 獲取當前場景資料
        current_scene = engine.get_current_scene()
        
        print("(思考中...)")
        
        # B. 意圖識別 (Intent Analysis)
        # 傳入 player 是為了讓分析器知道背包裡有什麼
        intent = analyzer.analyze(player_input, current_scene, player)
        print(f">> [Debug] {intent['action']} -> Target: {intent.get('target_id')}, Skill: {intent.get('skill_name')}")

        # C. 規則引擎處理 (Rule Execution)
        # Engine 內部會處理 Flags, Inventory, Dice, Stat Changes
        system_result = engine.process_intent(intent)

        # D. 敘事生成 (Narrative Generation)
        # 重新獲取場景 (因為可能移動了，或者狀態改變導致描述不同)
        new_scene = engine.get_current_scene()
        new_desc = engine.get_full_description(new_scene)
        setting = engine.get_setting()
        
        gm_response = narrator.narrate(new_desc, player_input, system_result, setting)
        print(f"\nGM: {gm_response}")

if __name__ == "__main__":
    main()