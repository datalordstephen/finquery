from rank_bm25 import BM25Okapi
from collections import defaultdict
from typing import List

# <--------- sparse embeddings ------------>
class BM25Retriever:
    def __init__(self, chunks):
        self.documents = [c["content"] for c in chunks]
        self.ids = [c["metadata"]["doc_id"] for c in chunks]
        
        tokenized_docs = [doc.lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(self.tokenized_docs)

    def search(self, query: str, k: int = 10):
        scores = self.bm25.get_scores(query.lower().split())

        ranked = sorted(
            zip(self.ids, scores),
            key=lambda x: x[1],
            reverse=True
        )[:k]

        return [
            {"doc_id": doc_id, "score": score}
            for doc_id, score in ranked
        ]

# <--------- rrf algo to combine dense + sparse search results ------------>
def rrf(ranked_lists, k: int = 60):
    """
    ranked_lists: List[List[{doc_id, score}]]
    """
    fused_scores = defaultdict(float)

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list):
            fused_scores[item["doc_id"]] += 1 / (k + rank + 1)

    res = sorted(fused_scores.items(), key=lambda x: x[1], reverse=True)
    return res 
