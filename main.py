import os
import json
from dotenv import load_dotenv
from ollama import Client

# 1. 載入環境變數
load_dotenv()
API_KEY = os.getenv("LLM_API_KEY")
HOST = os.getenv("API_HOST")
MODEL = os.getenv("MODEL_NAME", "llama3")

# 2. 初始化 LLM Client
client = Client(host=HOST, headers={'Authorization': f'Bearer {API_KEY}'})

# 3. 載入世界資料
with open('world_data.json', 'r', encoding='utf-8') as f:
    world_data = json.load(f)

# === 全域狀態 (FSM State) ===
current_scene_id = world_data["initial_scene"]
history = []  # 對話紀錄

def get_llm_narrative(scene_info, player_input):
    """
    這是 [中介層 Middleware]
    功能：組裝 Prompt 並呼叫 LLM
    """
    system_prompt = """
    你是一個 Call of Cthulhu (COC) 的守密人 (GM)。
    請根據提供的 [場景資訊] 和 [玩家行動]，描述接下來發生的事情。
    氣氛要懸疑、恐怖。請用繁體中文回答。
    """

    user_content = f"""
    [當前場景]: {scene_info}
    [玩家行動]: {player_input}
    """

    # 呼叫 API
    response = client.chat(
        model=MODEL,
        messages=[
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_content}
        ]
    )
    return response['message']['content']

def game_loop():
    global current_scene_id
    print("=== 遊戲開始 (輸入 'q' 離開) ===")
    
    # 初始描述
    current_scene = world_data["scenes"][current_scene_id]
    print(f"\nGM: {current_scene['base_description']}")

    while True:
        # 1. 接收玩家輸入
        player_input = input("\n你: ").strip()
        if player_input.lower() == 'q':
            break

        # 2. [規則引擎 Rule Engine] - 簡單的移動邏輯
        # 這裡未來會擴充成更複雜的意圖判斷
        current_scene = world_data["scenes"][current_scene_id]
        next_scene_id = None

        if "前" in player_input and "forward" in current_scene["exits"]:
            next_scene_id = current_scene["exits"]["forward"]["target"]
        elif "後" in player_input and "back" in current_scene["exits"]:
            next_scene_id = current_scene["exits"]["back"]["target"]

        # 3. 狀態更新
        narrative_context = current_scene["base_description"]
        if next_scene_id:
            current_scene_id = next_scene_id # 更新 FSM 狀態
            narrative_context += f"\n(系統判定: 玩家移動到了 {next_scene_id})"
        
        # 4. LLM 生成敘事
        print("GM (思考中)...")
        try:
            response = get_llm_narrative(narrative_context, player_input)
            print(f"\nGM: {response}")
        except Exception as e:
            print(f"連線錯誤: {e}")

if __name__ == "__main__":
    game_loop()