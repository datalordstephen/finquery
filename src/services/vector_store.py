import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from typing import List

embed_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)
        
def get_chroma_collection(path: str = "./chroma_db", name: str = "finquery"):
    """
    Initializes the ChromaDB collection and save to disk.
    """
    client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(name= name, embedding_function= embed_fn)

def add_documents(chunks: List):
    """
    Add processed chunks to ChromaDB collection.
    """
    collection = get_chroma_collection()

    ids = [c["metadata"]["doc_id"] for c in chunks]
    documents = [c["content"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # make use of custom embedding algo (jina-ai)
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"✓ Added {len(chunks)} chunks. Total in DB: {collection.count()}")
    return collection.count()

def query_dense(query_text: str, n_results: int = 5, filters: dict = None):
    """ Extract Filters from query using a hf model (NER?) 
    """
    collection = get_chroma_collection()

    query_results = collection.query(
        query_texts = [query_text],
        n_results=n_results,
        where = filters
    )
    
    results = [
        {
            "doc_id": doc_id,
            "content": doc,
            "metadata": meta,
            "score": 1 - distance  # Convert distance to similarity
        }
        for doc_id, doc, meta, distance in zip(
            query_results["ids"][0],
            query_results["documents"][0],
            query_results["metadatas"][0],
            query_results["distances"][0]
        )
    ]

    return results