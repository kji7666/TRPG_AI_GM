import chromadb
from chromadb.utils import embedding_functions
from src.util.logger import logger

class RAGRetriever:
    def __init__(self, db_path: str = "data/vector_db", collection_name: str = "trpg_knowledge"):
        logger.log("[RAGRetriever.__init__]", "system.txt")
        # 連接現有的資料庫
        self.client = chromadb.PersistentClient(path=db_path)
        # 使用同樣的多語言模型 (必須與 Ingestor 一致)
        self.embedding_func = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        # 同 ingestor, 取得 collect, 設定 embedding function
        self.collection = self.client.get_collection(
            name=collection_name,
            embedding_function=self.embedding_func
        )

    def query(self, text: str, n_results: int = 2) -> str:
        """
        搜尋最相關的知識片段，回傳純文字
        """
        logger.log("[RAGRetriever.query] 查詢 : " + text, "system.txt")
        try:
            results = self.collection.query(
                query_texts=[text],
                n_results=n_results
            )
            # {
            #   "ids": [[...]],
            #   "documents": [[...]], 長度 = 回傳文本數 = n_results
            #   "embeddings": [[...]],
            #   "distances": [[...]],
            #   "metadatas": [[...]]
            # }
            # 檢查是否有結果
            if not results["documents"] or not results["documents"][0]:
                return "（資料庫中沒有找到相關資訊）"

            docs = results["documents"][0]
            metas = results["metadatas"][0]

            # --- [關鍵修改] 將多筆資料拼起來 ---
            combined_response = f"關於「{text}」的檢索結果：\n"
            
            for i, (doc, meta) in enumerate(zip(docs, metas)):
                source = meta.get('source', '未知來源')
                combined_response += f"\n[資料 {i+1}] (來源: {source})\n"
                combined_response += f"{'-'*30}\n{doc}\n{'-'*30}\n"

            return combined_response

        except Exception as e:
            return f"檢索發生錯誤: {str(e)}"