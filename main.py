import os
import json
import random
from dotenv import load_dotenv
from ollama import Client
from intent_analyzer import IntentAnalyzer

# 1. 設定
load_dotenv()
API_KEY = os.getenv("LLM_API_KEY")
HOST = os.getenv("API_HOST")
MODEL = os.getenv("MODEL_NAME")

client = Client(host=HOST, headers={'Authorization': f'Bearer {API_KEY}'})
analyzer = IntentAnalyzer(client, MODEL)

# 2. 載入世界資料
with open('world_data.json', 'r', encoding='utf-8') as f:
    world_data = json.load(f)

# === 全域變數 ===
current_scene_id = world_data["initial_scene"]
game_flags = world_data["global_vars"]["flags"]

# === Mock Dice (簡易擲骰系統) ===
# 為了先測試 world_data，我們先假設玩家所有技能都是 50
def simple_roll(skill_name, difficulty):
    roll = random.randint(1, 100)
    player_skill_val = 50 # 預設值，之後接 player.json 再改
    
    success = roll <= player_skill_val
    result_type = "成功" if success else "失敗"
    
    return {
        "success": success,
        "roll": roll,
        "target": player_skill_val,
        "msg": f"(技能【{skill_name}】檢定: {roll}/{player_skill_val} -> {result_type})"
    }

# === 敘事生成 ===
def get_gm_response(scene_desc, player_input, system_result):
    system = """
    你是一個 Call of Cthulhu (COC) 的守密人 (GM)。
    你的任務是根據 [當前場景] 與 [系統判定結果] 進行敘事。

    【重要規則】
    1. **連貫性**：玩家已在場景中，不要描述「玩家走進來」。
    2. **禁止擅自行動**：只能描述看到了什麼，不要幫玩家拿走東西。
    3. **忠於設定 (最高優先)**：場景是現代地鐵車廂。**嚴禁憑空創造** JSON 描述中不存在的家具（如桌子、書櫃、鏡子）或狀態（如窗戶破裂）。如果描述沒寫，就代表沒有。
    4. **回答問題**：若結果是「玩家詢問資訊」，請直接在敘事中回答。
    5. **呈現檢定**：如果 [系統判定結果] 包含 "(技能【XX】檢定...)"，請在敘事中稍微帶到玩家努力的過程（例如：你仔細觀察...），而不只是給出結果。
    6. **語氣**：懸疑、恐怖、繁體中文。
    """
    user = f"""
    [當前場景]: {scene_desc}
    [玩家行動]: {player_input}
    [系統判定結果]: {system_result}
    """
    res = client.chat(model=MODEL, messages=[
        {'role': 'system', 'content': system},
        {'role': 'user', 'content': user}
    ])
    return res['message']['content']

# === 處理動態描述 (Context Overlay) ===
def get_full_description(scene):
    desc = scene['base_description']
    
    if "overlays" in scene:
        for overlay in scene["overlays"]:
            cond = overlay["condition"]
            is_met = False
            
            # 狀況 A: 處理數值比較 (例如: turn_count > 5)
            if ">" in cond:
                key, val_str = cond.split(">")
                key = key.strip()
                target_val = int(val_str.strip())
                
                # 從 global_vars 讀取數值 (例如 turn_count)
                # 注意：這裡讀的是 world_data["global_vars"]，而不是只讀 flags
                actual_val = world_data["global_vars"].get(key, 0)
                if actual_val > target_val:
                    is_met = True

            # 狀況 B: 處理相等比較 (例如: has_keys == true)
            elif "==" in cond:
                key, val_str = cond.split("==")
                key = key.strip()
                expected_val = val_str.strip().lower() == "true"
                
                # 從 flags 讀取布林值
                if game_flags.get(key) == expected_val:
                    is_met = True
            
            # 如果條件符合，將文字疊加到描述中
            if is_met:
                desc += f" {overlay['text']}"
                
    return desc

def game_loop():
    global current_scene_id
    print("=== COC Agent (Mock Dice Mode) ===")
    
    # 初始描述
    scene = world_data["scenes"][current_scene_id]
    desc = get_full_description(scene)
    print(f"\nGM: {desc}")

    while True:
        player_input = input("\n你: ").strip()
        if player_input.lower() in ['q', 'quit']:
            break

        scene = world_data["scenes"][current_scene_id]
        
        # 1. 意圖識別
        print(f"(系統思考中...)")
        intent = analyzer.analyze(player_input, scene)
        print(f">> 意圖: {intent['action']}, 目標: {intent['target_id']}")

        system_result = ""
        target_id = intent.get("target_id")

        # 2. 規則引擎
        if intent["action"] == "MOVE":
            if target_id and target_id in scene["exits"]:
                current_scene_id = target_id
                system_result = f"玩家移動到了 {target_id}。"
            else:
                system_result = "玩家想移動但方向不明。"

        elif intent["action"] == "INVESTIGATE":
            if target_id and target_id in scene.get("interactables", {}):
                item = scene["interactables"][target_id]
                
                # 檢查是否需要特殊旗標 (例如開門需要鑰匙)
                if item.get("type") == "item_req":
                    req = item["req_flag"]
                    if not game_flags.get(req, False):
                        system_result = f"互動失敗。{item['fail_msg']}"
                    else:
                        system_result = f"互動成功。{item['success_msg']}"
                        if "on_success" in item:
                            for k, v in item["on_success"].items():
                                # 簡單處理布林值
                                if v == "true": game_flags[k.split("=")[0]] = True

                # 檢查是否需要檢定 (Check)
                elif item.get("type") == "check":
                    skill = item.get("skill", "Spot Hidden")
                    diff = item.get("difficulty", 20)
                    
                    # 執行 Mock Dice
                    dice_res = simple_roll(skill, diff)
                    
                    if dice_res["success"]:
                        result_msg = item["success_msg"]
                        # 更新 Flag (例如拿到鑰匙)
                        if "on_success" in item:
                             for k, v in item["on_success"].items():
                                 flag_name = k.split("=")[0]
                                 game_flags[flag_name] = True
                    else:
                        result_msg = item["fail_msg"]

                    system_result = f"玩家調查 {target_id}。{dice_res['msg']}。結果：{result_msg}"
                
                else:
                    system_result = f"玩家觀察了 {target_id}。描述：{item['description']}"

            else:
                system_result = "玩家在找東西但沒發現什麼。"

        elif intent["action"] == "QUERY":
             desc = get_full_description(scene)
             system_result = f"玩家詢問資訊。目前位於 {current_scene_id}。場景狀態：{desc}"

        else:
            system_result = f"玩家進行其他動作：{intent.get('reason')}"

        # 3. 敘事生成
        # 重新抓取場景 (因為可能移動了)
        new_scene = world_data["scenes"][current_scene_id]
        new_desc = get_full_description(new_scene)
        
        response = get_gm_response(new_desc, player_input, system_result)
        print(f"\nGM: {response}")

if __name__ == "__main__":
    game_loop()