# debug_connection.py
import sys
from src.llm.client import llm_client

print("--- 只有連線測試 ---")

messages = [
    {"role": "user", "content": "Hello, are you alive? Reply with 'YES'."}
]

print("發送測試訊息...")
response = llm_client.chat(messages)

print(f"回應: [{response}]")

if not response:
    print("❌ 測試失敗：收到空回應")
else:
    print("✅ 測試成功")