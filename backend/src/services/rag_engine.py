from .vector_store import query_collection, query_multiple_collections, get_or_create_collection, list_all_documents
from .retrieval import BM25Retriever, rrf

class RAGEngine:
    """
    Multi-document RAG system.
    Can query single document or across multiple documents.

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
        self.bm25_cache = {}  # Cache BM25 retrievers per document
    
    def _get_bm25_retriever(self, doc_name = str):
        """
        Get or create BM25 retriever for a specific document.
        """
        # if it's only vector search
        if not self.use_hybrid:
            return None

        # Check cache
        if doc_name in self.bm25_cache:
            print("✓ Using cached BM25")
            return self.bm25_cache[doc_name]
        
        # Load from ChromaDB
        try:
            collection = get_or_create_collection(doc_name)
            if collection.count() == 0:
                return None
            
            all_docs = collection.get()
            chunks = [
                {
                    "content": doc,
                    "metadata": meta
                }
                for doc, meta in zip(all_docs["documents"], all_docs["metadatas"])
            ]
            
            retriever = BM25Retriever(chunks)
            self.bm25_cache[doc_name] = retriever
            print(f"✓ BM25 initialized for '{doc_name}' ({len(chunks)} chunks)")
            
            return retriever
        
        except Exception as e:
            print(f"Error initializing BM25 for {doc_name}: {e}")
            return None
    
    def retrieve_single_document(self, doc_name: str, query: str, n_results: int = 5) -> list:
        """
        Retrieve from a single document using hybrid search.
        """
        if not self.use_hybrid:
            return query_collection(doc_name, query, n_results)
        
        # Hybrid search
        dense_results = query_collection(doc_name, query, n_results * 2)
        
        bm25_retriever = self._get_bm25_retriever(doc_name)
        if bm25_retriever:
            print(f"✓ BM25 retrieved for '{doc_name}'")
            sparse_results = bm25_retriever.search(query, k=n_results * 2)
            fused = rrf([dense_results, sparse_results])
            return fused[:n_results]

        return dense_results[:n_results]

    def retrieve_multiple_documents(self, doc_names: list[str], query: str, n_results: int = 5) -> list:
        """
        Retrieve from multiple documents using hybrid search.
        """
        all_results = []
        
        for doc_name in doc_names:
            results = self.retrieve_single_document(doc_name, query, n_results)
            all_results.extend(results)
        
        # Sort by score and return top n_results
        all_results.sort(
            key=lambda x: x.get("score", x.get("fused_score", 0)),
            reverse=True
        )
        
        return all_results[:n_results]

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
            doc_id = chunk["doc_id"]
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

    def query(self, question: str, doc_names: list[str] | None = None, n_results: int = 5) -> dict:
        """
        Query one or multiple documents.
        
        Args:
            question: User's question
            doc_names: List of document names to search. If None, searches all.
            n_results: Number of chunks to retrieve
        
        Returns:
            dict with answer, sources, and context
        """
        # If no specific docs provided, search all
        if doc_names is None:
            all_docs = list_all_documents()
            doc_names = [doc["name"] for doc in all_docs]
        
        # can't search in an empty db
        if not doc_names:
            return {
                "answer": "No documents found in database. Please upload documents first.",
                "sources": [],
                "context": ""
            }

        # 1. Retrieve relevant chunks
        if len(doc_names) == 1:
            chunks = self.retrieve_single_document(doc_names[0], question, n_results)
        else:
            chunks = self.retrieve_multiple_documents(doc_names, question, n_results)

        # 2. Build context
        context, sources = self.build_context(chunks)
        
        # 3. Generate answer
        answer = self.generate_answer(context, question)

        return {
            "answer": answer,
            "sources": sources,
            "context": context,
            "searched_docs": doc_names
        }