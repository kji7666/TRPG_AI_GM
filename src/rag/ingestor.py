import os
import glob
import chromadb
from chromadb.utils import embedding_functions
from src.util.logger import logger

class RAGIngestor:
    def __init__(self, 
                 knowledge_dir: str = "data/knowledge", 
                 db_path: str = "data/vector_db",
                 collection_name: str = "trpg_knowledge"):
        logger.log("[RAGIngestor.__init__]", "system.txt")
        self.knowledge_dir = knowledge_dir 
        # 初始化 ChromaDB Client (持久化存儲到硬碟，下次重啟仍能繼續使用同一個向量資料庫)
        self.client = chromadb.PersistentClient(path=db_path)
        # 設定 Embedding 模型（用來把文字轉成向量）
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        # 取得或建立 Collection (類似 SQL 的 Table) 可儲存複數個
        # document（你放入的原始文字）
        # embedding（由模型計算出的向量）
        # metadata（額外資訊）
        # id（唯一識別碼）
        # 指定 embedding_function, 在 add 時自動呼叫
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_func
        )

    def _split_text(self, text: str) -> list[str]:
        """
        [切塊邏輯]
        簡單的依據「雙換行」來切分段落。
        針對我們的 lore.txt 格式 (【標題】...內容...)，這樣切分效果通常不錯。
        """
        logger.log("[RAGIngestor._split_text] 切分 txt", "system.txt")
        # 移除多餘空白
        text = text.strip()
        # 依據空行切分
        chunks = text.split("\n\n")
        # 過濾掉太短的碎片
        return [chunk.strip() for chunk in chunks if len(chunk.strip()) > 10]

    def ingest(self):
        """
        執行注入流程：讀檔 -> 切塊 -> 存入 DB
        """
        print(f"🚀 開始注入知識庫...")
        
        # 1. 讀取所有 .txt 檔案
        files = glob.glob(os.path.join(self.knowledge_dir, "*.txt"))
        if not files:
            print("⚠️ 警告: 找不到任何 .txt 檔案，請檢查 data/knowledge/")
            return

        # 2. 為了避免重複，我們先清空舊資料
        # 注意: ChromaDB 沒有直接 clear，我們先 delete 再 create
        try:
            self.client.delete_collection("trpg_knowledge")
            self.collection = self.client.get_or_create_collection(
                name="trpg_knowledge",
                embedding_function=self.embedding_func
            )
            print("🧹 已清空舊資料庫")
        except:
            pass

        total_chunks = 0
        
        for file_path in files:
            file_name = os.path.basename(file_path)
            print(f"📄 處理檔案: {file_name}")
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            # 切塊
            chunks = self._split_text(content)
            
            if not chunks:
                continue

            # 準備寫入 DB 的資料
            ids = [f"{file_name}_{i}" for i in range(len(chunks))]
            metadatas = [{"source": file_name} for _ in range(len(chunks))] # filename 對 chunk
            
            # 寫入 ChromaDB
            # 因為 Collection 有指定 embedding_function, 自動做：
            # chunk → embedding model → 向量 → 儲存
            self.collection.add(
                documents=chunks,
                ids=ids,
                metadatas=metadatas
            )
            total_chunks += len(chunks)
            print(f"   -> 寫入 {len(chunks)} 個片段")
        logger.log("[RAGIngestor.ingest] 把 chunk 寫進 db", "system.txt")
        print(f"✅ 注入完成！總共儲存了 {total_chunks} 個知識片段。")
        print(f"💾 資料庫位置: data/vector_db")

# 用於直接執行測試
if __name__ == "__main__":
    ingestor = RAGIngestor()
    ingestor.ingest()