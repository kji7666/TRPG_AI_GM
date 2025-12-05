from src.rag.ingestor import RAGIngestor

print("--- Phase 2: Step 2 知識注入測試 ---")

# 1. 執行注入 (建立圖書館)
ingestor = RAGIngestor()
ingestor.ingest()

print("\n--- 測試檢索 (Search Test) ---")

# 2. 模擬搜尋
query_text = "循聲者有什麼弱點？"
print(f"🔍 查詢: {query_text}")

# 改為找 3 筆
target_n_results = 3

results = ingestor.collection.query(
    query_texts=[query_text],
    n_results=target_n_results 
)

# 3. 顯示結果 (修改部分)
# ChromaDB 回傳格式是 List of List: results["documents"] = [[doc1, doc2, doc3]]
# 所以 results["documents"][0] 才是我們要的那組結果列表

if results["documents"] and results["documents"][0]:
    # 取得第一組查詢的所有結果
    docs_list = results["documents"][0]
    metas_list = results["metadatas"][0]
    
    print(f"\n✅ 找到 {len(docs_list)} 筆相關資料:")
    
    # 使用 zip 同時遍歷文件內容與 metadata
    for i, (doc, meta) in enumerate(zip(docs_list, metas_list)):
        print(f"\n[第 {i+1} 筆] (來源: {meta['source']})")
        print("-" * 30)
        print(doc)
        print("-" * 30)
else:
    print("❌ 找不到相關資料")

print("\n測試完成。")