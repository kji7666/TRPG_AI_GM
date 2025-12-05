import json
import os
from .models import Scenario
from src.util.logger import logger

class ScenarioLoader:
    def __init__(self, scenarios_dir="data/scenarios"):
        self.scenarios_dir = scenarios_dir

    def load(self, filename: str) -> Scenario:
        """
        讀取 JSON 並驗證格式，回傳 Scenario 物件
        """
        logger.log("[ScenarioLoader.load] load json to Scenario", "system.txt")
        path = os.path.join(self.scenarios_dir, filename)

        if not os.path.exists(path):
            raise FileNotFoundError(f"找不到劇本檔案: {path}")
        print(f"[Loader] 正在載入劇本: {path} ...")

        with open(path, 'r', encoding='utf-8') as f:
            raw_data = json.load(f) # JSON 讀進來之後會變成 Python 的 dict
        
        # Pydantic 會自動檢查 JSON 欄位是否對應 Class 定義
        # 如果 JSON 少了 "title" 或 exits 格式錯誤，這裡會直接報錯
        try:
            scenario = Scenario(**raw_data) # **kwargs 語法, 將 dict 展開成 param
            print(f"[Loader] 成功載入: {scenario.title} (包含 {len(scenario.nodes)} 個節點)")
            
            if scenario.start_node_id not in scenario.nodes: # 不能亂寫起點
                raise ValueError(f"錯誤：起始節點 {scenario.start_node_id} 不在 nodes 列表中！")
              
            return scenario
        except Exception as e:
            print(f"[Loader] 劇本格式驗證失敗: {e}")
            raise e

loader = ScenarioLoader()