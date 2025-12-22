from .vector_store import query_dense, get_chroma_collection
from .retrieval import BM25Retriever, rrf

class RAGEngine:
    """
    Complete RAG pipeline:
    1. Hybrid retrieval (dense + sparse)
    2. Reranking with RRF
    3. Context building
    4. LLM generation
    """
    
    def __init__(self, llm_client, use_hybrid: bool = True):
        """
        Args:
            llm_client: OpenAI/Together API client
            use_hybrid: Enable BM25 + vector search (slower but better)
        """
        self.llm_client = llm_client
        self.use_hybrid = use_hybrid
        self.bm25_retriever = None
        
        # Initialize BM25 if hybrid mode
        if use_hybrid:
            self._init_bm25()
    
    def _init_bm25(self):
        """Load all docs from ChromaDB to initialize BM25."""
        collection = get_chroma_collection()
        
        # Get all documents
        all_docs = collection.get()
        
        chunks = [
            {
                "content": doc,
                "metadata": meta
            }
            for doc, meta in zip(all_docs["documents"], all_docs["metadatas"])
        ]
        
        if chunks:
            self.bm25_retriever = BM25Retriever(chunks)
            print(f"BM25 initialized with {len(chunks)} documents")

    def retrieve(self, query: str, n_results: int = 5) -> list:
        """
        Retrieve relevant chunks using hybrid search.
        
        Returns:
            List of dicts with 'doc_id', 'content', 'metadata', 'score'
        """
        # Dense-only retrieval
        if not self.use_hybrid or self.bm25_retriever is None:
            return query_dense(query, n_results=n_results)
        
        # Hybrid retrieval
        dense_results = query_dense(query, n_results=n_results * 2)
        sparse_results = self.bm25_retriever.search(query, k=n_results * 2)
        
        fused = rrf([dense_results, sparse_results])
        
        return fused[:n_results]

    def build_context(self, chunks: list) -> tuple[str, list]:
        """
        Convert retrieved chunks into context string.
        
        Returns:
            (context_string, sources)
        """
        if not chunks:
            return "", []
        
        context_parts = []
        sources = []
        
        for i, chunk in enumerate(chunks, 1):
            doc_id = chunk["metadata"]["doc_id"]
            content = chunk["content"]
            
            context_parts.append(f"[Chunk {i}] doc_id: {doc_id}\n{content}")
            sources.append({
                "doc_id": doc_id,
                "page": chunk["metadata"].get("page"),
                "type": chunk["metadata"].get("type"),
                "score": chunk.get("score", chunk.get("fused_score", 0))
            })
        
        context_str = "\n\n---\n\n".join(context_parts)
        return context_str, sources

    def generate_answer(self, context: str, query: str) -> str:
        """Generate answer using LLM."""

        system_prompt = """
You are an expert financial analysis assistant.

Answer questions using ONLY the provided context chunks. Each chunk has a `doc_id` format:
<document>::page_<number>::<type>_<index>

CORE RULES:
1. Use ONLY provided context - never use prior knowledge
2. If answer not in context, say: "The documents don't contain sufficient information"
3. Cite every fact using: "Source: <doc>, page <num> (Table/Text <idx>)"

TABLE HANDLING:
- Tables in Markdown format are authoritative sources of truth
- Extract exact values from relevant rows/columns  
- If question mentions "the table" or specific data points, prioritize table over prose
- Preserve exact figures, units, currencies, dates
- Never recalculate or round numbers

CITATION FORMAT:
Source: msft_10k_2023.pdf, page 42 (Table 1, Row 3)
Source: report.pdf, page 15 (Text 2)

Be precise, factual, and always cite sources.
"""
        if not context:
            print("No Context Found")
            return "I couldn't find relevant information in the documents to answer your question."
        
        user_prompt = f"""
Context: {context}

Question: {query}

Answer:"""
        
        try:
            response = self.llm_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=1000
            )
            
            return response.choices[0].message.content
        
        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def query(self, question: str, n_results: int = 5) -> dict:
        """
        End-to-end RAG pipeline.
        
        Returns:
            {
                "answer": str,
                "sources": list,
                "context": str (for debugging)
            }
        """
        # 1. Retrieve relevant chunks
        chunks = self.retrieve(question, n_results=n_results)
        
        # 2. Build context
        context, sources = self.build_context(chunks)
        
        # 3. Generate answer
        answer = self.generate_answer(context, question)
        
        return {
            "answer": answer,
            "sources": sources,
            "context": context  # Include for debugging
        }