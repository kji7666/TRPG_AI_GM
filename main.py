import sys
import os
import json
import time
import traceback

# 引入核心模組
from src.core.state import GameState, PlayerState, WorldState, NPCState
from src.core.tools import UniversalTools
from src.core.event_engine import EventEngine
from src.core.npc_engine import npc_engine  
from src.core.memory import MemoryManager
from src.llm.agent import ReActAgent
from src.scenarios.loader import loader
from src.util.logger import logger

def main():
    # 確保日誌目錄存在
    if not os.path.exists("data/logs"):
        os.makedirs("data/logs")

    logger.log("[main] start", "system.txt")

    print("==========================================")
    print("   Cthulhu AI GM Engine (Robust Ver.)     ")
    print("==========================================")

    # --- 1. 載入資料 ---
    print("Loading resources...")
    
    # Load 劇本
    try:
        scenario = loader.load("dark_compartment.json")
    except Exception as e:
        print(f"❌ 劇本載入失敗: {e}")
        traceback.print_exc()
        return

    # Load Player
    player_file = "data/players/player.json"
    if os.path.exists(player_file):
        with open(player_file, "r", encoding="utf-8") as f:
            try:
                player_data = json.load(f)
                player = PlayerState(**player_data)
            except Exception as e:
                print(f"⚠️ 玩家檔案格式錯誤: {e}，使用預設角色。")
                player = PlayerState(name="測試員")
    else:
        print("⚠️ 找不到 player.json，使用預設角色。")
        player = PlayerState(name="測試員")

    # 設定初始位置
    world = WorldState(current_node_id=scenario.start_node_id)
    
    # 初始化 NPC
    if hasattr(scenario, 'npcs'): # [防呆] 確保 npcs 欄位存在
        print(f"Initializing {len(scenario.npcs)} NPCs...")
        for npc_def in scenario.npcs:
            npc_state = NPCState(
                id=npc_def.id,
                name=npc_def.name,
                description=npc_def.description,
                personality=npc_def.personality,
                motivation=npc_def.motivation,
                dialogue_style=npc_def.dialogue_style,
                location=npc_def.initial_location,
                status=npc_def.initial_status
            )
            world.npcs[npc_def.id] = npc_state

    # 建立核心狀態
    game = GameState(player=player, world=world, scenario=scenario)
    
    # 建立工具、Agent 與 事件引擎
    tools = UniversalTools(game)
    agent = ReActAgent(tools, max_steps=10)
    event_engine = EventEngine(game, tools)

    logger.log("[main] 初始化結束", "system.txt")
    print("\n✅ 系統就緒。")
    print(f"調查員: {player.name} (HP: {player.stats.HP}, SAN: {player.stats.SAN})")
    print("------------------------------------------")

    # 運行時變數
    last_turn_events = ""
    last_npc_reaction = ""
    chat_history_buffer = []
    BUFFER_LIMIT = 6 

    # --- 遊戲主迴圈 ---
    try:
        while True:
            logger.log("[main] 迴圈開始", "system.txt")
            current_node_id = game.world.current_node_id
            
            # 初始化變數
            room_info = None
            visible_items_objs = []
            
            # A. 獲取當前場景資訊 (含防呆)
            if current_node_id in scenario.nodes:
                room_info = scenario.nodes[current_node_id]
                
                # [防呆] 處理物品查找：確保 item_id 真的存在於全域定義中
                for item_id in room_info.items:
                    if not game.world.taken_items.get(item_id):
                        if item_id in scenario.items:
                            visible_items_objs.append(scenario.items[item_id])
                        else:
                            # 記錄警告但不崩潰
                            logger.log(f"[Warning] Room {current_node_id} contains undefined item: {item_id}", "error.txt")
            else:
                # [防呆] 如果 AI 移動到了不存在的房間 ID
                logger.log(f"[Warning] Invalid Node ID: {current_node_id}", "error.txt")
                room_desc = f"【未知區域 ({current_node_id})】\n這裡是一片虛無... (系統錯誤：無效的地點 ID)"

            # =========================================================
            # [功能 A] 自動場景描述
            # =========================================================
            # [防呆] 只有當房間有效時才觸發自動描述，避免 RAG 查不到東西
            if room_info and current_node_id not in game.world.visited_nodes:
                print(f"\n🚀 [系統] 初次進入區域，正在生成描述...")
                
                game.world.visited_nodes.append(current_node_id)
                
                # [防呆] 確保 tags 存在
                scene_tags = " ".join(room_info.tags) if room_info.tags else current_node_id
                
                auto_input = f"""
[系統強制指令 System Override]
玩家剛剛進入了新場景：「{room_info.name}」。
場景標籤 (Tags): {scene_tags}

請執行以下步驟：
1. **必須** 呼叫 `search_knowledge` 查詢該場景的詳細視覺、聽覺、氣味描述。
2. 根據查詢結果，以陰鬱恐怖的風格描述玩家眼前的景象。
3. **不要** 進行任何檢定或互動，僅進行「環境描寫」。
"""
                logger.log("\nKP 正在觀察環境...", "think.txt")
                print("\nKP 正在觀察環境...")

                try:
                    response = agent.step(
                        user_input=auto_input,
                        summary=game.world.history_summary,
                        recent_history=chat_history_buffer
                    )
                    logger.log(f"\n💀 KP: {response}", "think.txt")
                    print(f"\n💀 KP: {response}")
                    chat_history_buffer.append(f"System: 進入 {current_node_id}")
                    chat_history_buffer.append(f"KP: {response}")
                except Exception as e:
                    print(f"❌ 自動描述生成失敗: {e}")
                
                continue
            # =========================================================


            # --- 以下為標準互動流程 ---

            # B. 顯示簡易介面
            room_name_display = f"【{room_info.name}】" if room_info else f"【{current_node_id}】"
            logger.log(f"\n📍 你位於: {room_name_display}", "think.txt")
            print(f"\n📍 你位於: {room_name_display}")
            
            if visible_items_objs:
                item_names = [i.name for i in visible_items_objs]
                print(f"   可見物品: {', '.join(item_names)}")

            # [防呆] 檢查並顯示同位置 NPC (解決 list has no attribute values 錯誤)
            present_npcs = []
            if isinstance(game.world.npcs, dict):
                present_npcs = [npc for npc in game.world.npcs.values() if npc.location == current_node_id]
            elif isinstance(game.world.npcs, list):
                # 如果 AI 真的把它改成了 list，嘗試兼容
                present_npcs = [npc for npc in game.world.npcs if hasattr(npc, 'location') and npc.location == current_node_id]
            
            if present_npcs:
                npc_names = ", ".join([f"{n.name} ({n.status})" for n in present_npcs])
                print(f"   人物: {npc_names}")
            
            if last_turn_events:
                print(f"\n🔔 {last_turn_events}")

            # C. 玩家輸入
            user_input = input("\n> ").strip()
            logger.log("[main] 玩家輸入: " + user_input, "system.txt")

            if user_input.lower().startswith("/save"):
                try:
                    msg = game.save_to_file()
                    print(f"💾 {msg}")
                except Exception as e:
                    print(f"❌ 存檔失敗: {e}")
                continue

            if user_input.lower().startswith("/load"):
                try:
                    new_game = GameState.load_from_file(scenario)
                    game = new_game
                    tools.game = new_game
                    agent.tools = tools
                    event_engine.game = new_game
                    chat_history_buffer = [] 
                    print(f"📂 讀檔成功！回到第 {game.world.turn_count} 回合。")
                    continue
                except Exception as e:
                    print(f"❌ 讀檔失敗: {e}")
                continue

            if user_input.lower() in ["q", "quit", "exit"]:
                print("再見。")
                break
            
            if not user_input:
                continue

            # --- D. 構建 Context ---
            items_context = ""
            if visible_items_objs:
                items_context = "\n[可見物品 (僅知外觀，詳細內容未知)]:\n" + "\n".join([f"- {i.name}" for i in visible_items_objs])
            
            event_context = ""
            if last_turn_events:
                event_context = f"\n[剛剛發生的突發事件]:\n{last_turn_events}"
                
            npc_context = ""
            if present_npcs:
                npc_context = "\n[場景中的 NPC]:\n" + "\n".join([f"- {n.name} (狀態: {n.status})" for n in present_npcs])
            
            if last_npc_reaction:
                npc_context += f"\n[NPC 剛才的反應]: {last_npc_reaction}"

            ending_context = ""
            # [防呆] 確保 endings 屬性存在
            if (current_node_id == "car_1" or current_node_id == "car_1_internal") and hasattr(scenario, 'endings'): 
                ending_context = "\n[結局觸發條件 (請根據玩家行動判定)]:\n"
                for end in scenario.endings:
                    ending_context += f"- 若 {end.condition_desc} -> 觸發結局 {end.name}\n"

            # [功能 B] 系統強制注入
            system_injection = ""
            trigger_words = ["看", "讀", "檢查", "調查", "搜尋", "翻", "check", "read", "inspect", "search", "examine"]
            is_investigating = any(w in user_input.lower() for w in trigger_words)
            
            target_item_name = None
            if is_investigating and visible_items_objs:
                for item in visible_items_objs:
                    if item.name in user_input:
                        target_item_name = item.name
                        break
            
            if target_item_name:
                logger.log(f"[System] 偵測調查意圖: {target_item_name}", "system.txt")
                system_injection = f"""
🔴 [系統強制指令 System Override]
玩家正在試圖調查「{target_item_name}」。
**你必須立刻呼叫 `search_knowledge` 工具，查詢 "{target_item_name}" 的詳細內容。**
"""

            full_context = f"""
[場景]: {room_info.name if room_info else '無'}
{items_context}
{npc_context}
{event_context}
{ending_context}
{system_injection}
[玩家行動]: {user_input}
"""
            
            # --- E. Agent 思考與行動 ---
            print("\nKP 正在思考...")
            logger.log("\nKP 正在思考...", "think.txt")
            
            try:
                response = agent.step(
                    user_input=full_context, 
                    summary=game.world.history_summary, 
                    recent_history=chat_history_buffer
                )
                print(f"\n💀 KP: {response}")
                logger.log(f"\n💀 KP: {response}", "think.txt")
                
                # --- F. 記憶管理 ---
                chat_history_buffer.append(f"Player: {user_input}")
                chat_history_buffer.append(f"KP: {response}")
                
                if len(chat_history_buffer) >= BUFFER_LIMIT:
                    print("\n🧠 [系統] 正在整理長期記憶...")
                    try:
                        new_summary = MemoryManager.summarize(
                            game.world.history_summary, 
                            chat_history_buffer
                        )
                        game.world.history_summary = new_summary
                        chat_history_buffer = chat_history_buffer[-2:] 
                    except Exception as e:
                        print(f"⚠️ 記憶摘要失敗 (跳過): {e}")

            except Exception as e:
                print(f"❌ Agent 執行錯誤: {e}")
                traceback.print_exc()

            # --- G. NPC 反應 ---
            last_npc_reaction = ""
            for npc in present_npcs:
                if npc.status == "alive" and npc.location == current_node_id:
                    print(f"\n({npc.name} 正在觀察你...)")
                    logger.log(f"\n({npc.name} 正在觀察你...)", "think.txt")
                    
                    try:
                        npc_observation = f"場景: {room_info.name}\n玩家做了: {user_input}\nKP描述: {response}"
                        reaction = npc_engine.react(npc, user_input, npc_observation, history=chat_history_buffer)
                        
                        dialogue = reaction.get("dialogue", "...")
                        action = reaction.get("action", "")
                        
                        print(f"💬 {npc.name}: 「{dialogue}」")
                        print(f"   (動作: {action})")
                        
                        reaction_text = f"{npc.name} 說：「{dialogue}」並做了動作：{action}"
                        last_npc_reaction += reaction_text + "\n"
                        chat_history_buffer.append(f"NPC ({npc.name}): {dialogue} ({action})")
                    except Exception as e:
                        print(f"⚠️ NPC 反應失敗: {e}")

            # --- H. 時間與事件 ---
            game.world.turn_count += 1
            triggered_messages = event_engine.process_events(trigger_type="turn_end")
            if triggered_messages:
                last_turn_events = "\n".join(triggered_messages)
            else:
                last_turn_events = ""

    except KeyboardInterrupt:
        print("\n\n⚠️ 強制中斷。")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 發生未預期錯誤: {e}")
        logger.log(f"[main] Error: {e}", "error.txt")
        traceback.print_exc()

if __name__ == "__main__":
    main()