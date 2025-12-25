import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
import os

embed_fn = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

# <--------------- complete overhaul to allow for a multi-collection system ----------------->
def get_chroma_client(path: str = "./chroma_db"):
    """Get persistent ChromaDB client."""
    return chromadb.PersistentClient(path=path)

def create_collection_name(doc_name: str) -> str:
    """
    Convert document filename to valid collection name.
    ChromaDB collection names must be 3-63 chars, alphanumeric + underscores/hyphens.
    """
    # Remove extension
    name = os.path.splitext(doc_name)[0]
    
    # Replace invalid chars with underscores
    name = name.replace(" ", "_").replace(".", "_")
    
    # Ensure starts with letter/digit
    if not name[0].isalnum():
        name = "doc_" + name
    
    # Truncate to 63 chars
    name = name[:63].lower()
    
    return name

def get_or_create_collection(doc_name: str, path: str = "./chroma_db", pages: int = None, creating : bool = False):
    """
    Get or create a collection for a specific document.
    Each document gets its own collection.
    Store number of pages as metadata.
    """
    client = get_chroma_client(path)
    collection_name = create_collection_name(doc_name)

    # add metadata if we're creating the document. else just retrieve
    if creating:
        metadata = {
            "pages": pages,
            "filename": doc_name
        }

        return client.create_collection(
            name=collection_name,
            embedding_function=embed_fn,
            metadata=metadata
        )
    else:
        return client.get_collection(
            name=collection_name,
            embedding_function=embed_fn,
        )

def add_documents(chunks: list, doc_name: str, pages: int = None) -> dict:
    """
    Add processed chunks to a specific collection.
    
    Args:
        chunks: List of processed chunks from ingest.py
        doc_name: Original document filename
    
    Returns:
        dict with collection_name and count
    """
    collection = get_or_create_collection(doc_name, pages=pages, creating=True)

    ids = [c["metadata"]["doc_id"] for c in chunks]
    documents = [c["content"] for c in chunks]
    metadatas = [c["metadata"] for c in chunks]

    # make use of custom embedding algo (jina-ai)
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )

    print(f"✓ Added {len(chunks)} chunks to collection {collection.name}.")
    return {
        "collection_name": collection.name,
        "total_docs": collection.count()
    }

def query_collection(
    doc_name: str,
    query_text: str,
    n_results: int = 5,
    filters: dict = None
    ):

    """ 
    Query a specific document's collection.
    """
    collection = get_or_create_collection(doc_name)

    if collection.count() == 0:
        return []

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

def query_multiple_collections(
    doc_names: list[str],
    query_text: str,
    n_results: int = 5
):
    """
    Query across multiple (or single) document collections.
    Returns combined results sorted by score.
    """
    all_results = []
    
    for doc_name in doc_names:
        results = query_collection(doc_name, query_text, n_results)
        all_results.extend(results)
    
    # Sort by score and return top n_results
    all_results.sort(key=lambda x: x["score"], reverse=True)
    return all_results[:n_results]

def list_all_documents(path: str = "./chroma_db") -> list[dict]:
    """
    List all document collections in the database.
    """
    client = get_chroma_client(path)
    collections = client.list_collections()
    
    documents = []
    for col in collections:
        pages = col.metadata.get("pages", None)
        filename = col.metadata.get("filename", col.name)
        
        documents.append({
            "name": filename,
            "count": col.count(),
            "pages": pages 
        })
    
    return documents

def delete_document_collection(doc_name: str, path: str = "./chroma_db"):
    """
    Delete a specific document's collection.
    """
    client = get_chroma_client(path)
    collection_name = create_collection_name(doc_name)
    
    try:
        client.delete_collection(collection_name)
        return True
    except Exception as e:
        print(f"Error deleting collection: {e}")
        return False

def get_collection_stats(doc_name: str) -> dict:
    """
    Get statistics for a specific document collection.
    """
    try:
        collection = get_or_create_collection(doc_name)
        return {
            "name": collection.name,
            "count": collection.count(),
            "exists": True
        }
    except Exception:
        return {
            "name": create_collection_name(doc_name),
            "count": 0,
            "exists": False
        }