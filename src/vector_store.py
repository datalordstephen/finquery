import chromadb
from chromadb.utils.embedding_functions import HuggingFaceEmbeddingFunction
from typing import List
from dotenv import load_dotenv
import os

load_dotenv()

embed_fn = HuggingFaceEmbeddingFunction(
            api_key=os.getenv("HF_API_KEY"),
            model_name="jina-embeddings-v2-small-en"
        )
        
def get_chroma_collection(path: str = "./chroma_db", name: str = "finquery"):
    """
    Initializes the ChromaDB collection and save to disk.
    """
    client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(name= name, embedding_function= embed_fn)

def add_documents(chunks: list):
    """
    Add processed chunks to ChromaDB collection.
    """
    collection = get_chroma_collection()

    ids = [c['metadata']["doc_id"] for c in chunks]
    documents = [c['content'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]
    
    # make use of custom embedding algo (jina-ai)
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"Total records in DB: {collection.count()}")

def query(query_text: str, n_results: int =5, filters: dict = None):
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
            "score": distance
        }
        for doc_id, distance in zip(
            results["ids"][0],
            results["distances"][0]
        )
    ]

    return results