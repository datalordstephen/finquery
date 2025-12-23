from rank_bm25 import BM25Okapi
from collections import defaultdict
from typing import List

# <--------- sparse embeddings ------------>
class BM25Retriever:
    def __init__(self, chunks):
        """Initialize BM25 with document chunks."""
        self.documents = [c["content"] for c in chunks]
        self.ids = [c["metadata"]["doc_id"] for c in chunks]
        self.metadatas = [c["metadata"] for c in chunks]
        
        tokenized_docs = [doc.lower().split() for doc in self.documents]
        self.bm25 = BM25Okapi(tokenized_docs)

    def search(self, query: str, k: int = 10) -> List:
        """Sparse keyword search."""
        scores = self.bm25.get_scores(query.lower().split())

        ranked = sorted(
            zip(self.ids, self.documents, self.metadatas, scores),
            key=lambda x: x[3],
            reverse=True
        )[:k]

        return [
            {
                "doc_id": doc_id,
                "content": content,
                "metadata": metadata,
                "score": score
            }
            for doc_id, content, metadata, score in ranked
        ]

# <--------- rrf algo to combine dense + sparse search results ------------>
def rrf(ranked_lists, k: int = 60):
    """
    Combine multiple ranked lists using RRF algorithm.
    
    Args:
        ranked_lists: List of lists, each containing dicts with 'doc_id' and 'score'
        k: RRF constant (default 60)
    
    Returns:
        List of doc_ids sorted by fused score
    """
    fused_scores = defaultdict(float)
    doc_map = {}

    for ranked_list in ranked_lists:
        for rank, item in enumerate(ranked_list):
            doc_id = item["doc_id"]
            fused_scores[doc_id] += 1 / (k + rank + 1)

            # Keep doc content and metadata
            if doc_id not in doc_map:
                doc_map[doc_id] = item

    # Sort by fused score
    sorted_ids = sorted(
        fused_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )
    
    # Return full doc info with fused scores
    return [
        {**doc_map[doc_id], "fused_score": score}
        for doc_id, score in sorted_ids
    ]
