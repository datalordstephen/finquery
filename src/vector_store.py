import chromadb

def get_chroma_collection(path: str = "./chroma_db", name: str = "finquery"):
    """
    Initializes the ChromaDB collection and save to disk.
    """
    client = chromadb.PersistentClient(path=path)
    return client.get_or_create_collection(name=name)

def add_documents(collection, chunks: list, embeddings):
    """
    Add processed chunks to ChromaDB collection.
    """
    ids = [f"page_{c['metadata']['page']}_chunk_{c['metadata']['chunk_id']}" for i, c in enumerate(chunks)]
    documents = [c['content'] for c in chunks]
    metadatas = [c['metadata'] for c in chunks]
    
    # make use of custom embedding algo (jina-ai)
    collection.add(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings = embeddings
    )

    len_records = collection.count()
    print(f"Added {len_records} chunks to database.")

def query(collection, query_emb: str, n_results:int =5, filters: dict = None):
    """ Extract Filters from query using a hf model (NER?) 
    """

    return collection.query(
        query_embeddings = query_emb,
        n_results=n_results,
        where = filters
    )