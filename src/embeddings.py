from chromadb.utils.embedding_functions import HuggingFaceEmbeddingFunction

class EmbeddingService:
    def __init__(self, api_key: str):
        self.client = HuggingFaceEmbeddingFunction(
            api_key = api_key, 
            model_name = "jina-embeddings-v2-small-en"
        )
    
    def generate_embedding(self, query: str):
        """Generate embedding for query"""
        response = self.client([query])

        return response



