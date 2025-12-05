import os
import datetime

class Logger:
    @staticmethod
    def log(msg: str, filename: str = "system.txt"):
        """
        寫入 Log 到 data/logs 資料夾
        """
        # 1. 確保 Log 目錄存在
        log_dir = "data/logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            
        # 2. 組合完整路徑
        file_path = os.path.join(log_dir, filename)
        
        # 4. 寫入檔案
        try:
            with open(file_path, 'a', encoding='utf-8') as f:
                f.write(msg + "\n")
        except Exception as e:
            print(f"❌ Log 寫入失敗: {e}")

# 方便外部直接調用
logger = Logger()