import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("LLM_API_KEY")
HOST = os.getenv("API_HOST")

def get_available_models():
    # 記得：Ollama 的 tags 路徑是 /api/tags
    # 如果 HOST 結尾已經有 /api，要注意不要重複
    # 根據你的 .env，HOST 是 https://api-gateway.netdb.csie.ncku.edu.tw
    url = f"{HOST}/api/tags"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}"
    }
    
    print(f"正在查詢可用模型: {url} ...")
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ 成功！伺服器允許你使用的模型如下：")
            print("------------------------------------------------")
            for model in data.get('models', []):
                print(f"名稱: {model['name']}")
            print("------------------------------------------------")
            print("請複製上面的 '名稱'，填入 .env 檔案的 MODEL_NAME 欄位。")
        else:
            print(f"❌ 查詢失敗 (Status: {response.status_code})")
            print(response.text)
            
    except Exception as e:
        print(f"發生錯誤: {e}")

if __name__ == "__main__":
    get_available_models()