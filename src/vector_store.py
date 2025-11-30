import chromadb

def get_chroma_collection(path: str = "./chroma_db", name: str = "financial_docs"):
    """
    Initializes the ChromaDB collection and save to disk.
    """
    client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(name=name)

def add_documents(collection, chunks: list):
    """
    Add processed chunks to ChromaDB collection.
    """
    ids = [f"doc_{i}_{hash(c['content'])}" for i, c in enumerate(chunks)]
    documents = [c['content'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]
    
    # chroma uses default embedding algo.
    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas
    )
    print(f"Upserted {len(documents)} chunks to database.")

def query(collection, query_text: str, n_results:int =5):
    return collection.query(
        query_texts=[query_text],
        n_results=n_results
    )