from .vector_store import query_collection, get_or_create_collection, list_all_documents
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
    
    def _get_bm25_retriever(self, doc_name = str, user_id: str  = None):
        """
        Get or create BM25 retriever for a specific document.
        """
        # if it's only vector search
        if not self.use_hybrid:
            return None

        cache_key = f"{user_id}_{doc_name}" if user_id else doc_name

        # Check cache
        if cache_key in self.bm25_cache:
            print("✓ Using cached BM25")
            return self.bm25_cache[cache_key]
        
        # Load from ChromaDB
        try:
            collection = get_or_create_collection(doc_name, user_id)
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
            self.bm25_cache[cache_key] = retriever
            print(f"✓ BM25 initialized for '{doc_name}' ({len(chunks)} chunks)")
            
            return retriever
        
        except Exception as e:
            print(f"Error initializing BM25 for {doc_name}: {e}")
            return None
    
    def retrieve_single_document(self, doc_name: str, query: str, user_id: str = None, n_results: int = 5) -> list:
        """
        Retrieve from a single document using hybrid search.
        """
        if not self.use_hybrid:
            return query_collection(doc_name, query, n_results, user_id=user_id)
        
        # Hybrid search
        dense_results = query_collection(doc_name, query, n_results * 2, user_id=user_id)
        
        bm25_retriever = self._get_bm25_retriever(doc_name, user_id)
        if bm25_retriever:
            print(f"✓ BM25 retrieved for '{doc_name}'")
            sparse_results = bm25_retriever.search(query, k=n_results * 2)
            fused = rrf([dense_results, sparse_results])
            return fused[:n_results]

        return dense_results[:n_results]

    def retrieve_multiple_documents(self, doc_names: list[str], query: str, user_id: str = None, n_results: int = 5) -> list:
        """
        Retrieve from multiple documents using hybrid search.
        """
        all_results = []
        
        for doc_name in doc_names:
            results = self.retrieve_single_document(doc_name, query, user_id, n_results=n_results)
            all_results.extend(results)
        
        # Sort by score and return top n_results
        all_results.sort(
            key=lambda x: x.get("score", x.get("fused_score", 0)),
            reverse=True
        )
        
        return all_results[:n_results]

    def build_context(self, chunks: list) -> tuple[str, list]:
        """
        Convert retrieved chunks into context string with clean source info.
        
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
            chunk_type = chunk["metadata"].get("type")
            page = chunk["metadata"].get("page")

            # Extract filename from doc_id (format: filename::page_X::type_Y)
            filename = doc_id.split("::")[0]
            
            # Build clean source reference
            if chunk_type == "table":
                source_ref = f"{filename}, page {page} (Table {chunk["metadata"].get("table_num", "")})"
            else:
                source_ref = f"{filename}, page {page}"
            
            context_parts.append(f"[Source: {source_ref}]\n{content}")
            sources.append({
                "filename": filename,
                "page": page,
                "type": chunk_type,
                "score": chunk.get("score", chunk.get("fused_score", 0))
            })
        
        context_str = "\n\n---\n\n".join(context_parts)
        return context_str, sources

    def _get_system_prompt(self) -> str:
        """Get the system prompt for LLM generation."""
        return """
You are FinQuery, an intelligent financial document assistant.

IDENTITY & PURPOSE:
- You help users find information in their uploaded financial documents
- You're knowledgeable, precise, and cite your sources

CONVERSATIONAL RULES:
- If greeted: Respond warmly and ask how you can help
- If asked about capabilities: Explain you analyze financial documents
- If thanked: Acknowledge gracefully
- For unclear questions: Ask for clarification

DOCUMENT ANALYSIS RULES:
1. Analyze the provided context chunks carefully
2. If you find relevant information: Answer the question directly and cite your sources
3. If you find PARTIAL information: Answer what you can find and note what's missing
4. ONLY if you find NO relevant information at all: Say you couldn't find it

CITATION FORMAT:
- Always cite: "Source: <filename>, page <number>"
- For tables: "Source: <filename>, page <number> (Table)"
- Cite ALL sources you use in your answer

TABLE HANDLING:
- Tables are authoritative for numerical data
- Extract exact values - never modify or round numbers
- Preserve currencies, dates, and units exactly as shown

ANSWER DIRECTLY:
- Don't say "I couldn't find..." if you actually found the information
- If the context contains the answer, state it clearly with sources
- Be confident when information is present

IMPORTANT:
- If you found the answer in the context, DO NOT say you couldn't find it
- Always cite exact sources
- Preserve exact numbers, currencies, and dates from tables
- Answer in prose, never in table format
- NEVER include raw markdown table syntax (|, ---, etc.) in your answer

TONE: Professional, precise, and helpful.
"""

    def generate_answer(self, context: str, query: str) -> str:
        """Generate answer using LLM (non-streaming)."""
        if not context:
            return "I couldn't find relevant information in the documents to answer your question."

        system_prompt = self._get_system_prompt()
        user_prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"

        try:
            response = self.llm_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
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

    def generate_answer_stream(self, context: str, query: str):
        """Generate answer using LLM with streaming. Yields tokens as they arrive."""
        if not context:
            yield "I couldn't find relevant information in the documents to answer your question."
            return

        system_prompt = self._get_system_prompt()
        user_prompt = f"Context: {context}\n\nQuestion: {query}\n\nAnswer:"

        try:
            response = self.llm_client.chat.completions.create(
                model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0,
                max_tokens=1000,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content

        except Exception as e:
            yield f"Error generating answer: {str(e)}"

    def query(self, question: str, doc_names: list[str] | None = None, user_id: str = None, n_results: int = 5) -> dict:
        """
        Query one or multiple documents.
        
        Args:
            question: User's question
            doc_names: List of document names to search. If None, searches all.
            user_id: User ID for document ownership verification
            n_results: Number of chunks to retrieve
        
        Returns:
            dict with answer, sources, and context
        """

        #  Check if it's a conversational query (no RAG needed)
        conversational_response = self._handle_conversational_query(question)
        if conversational_response:
            return {
                "answer": conversational_response,
                "sources": [],
                "context": None,
                "searched_docs": []
            }
        
        # If no specific docs provided, search all
        if doc_names is None:
            all_docs = list_all_documents(user_id)
            doc_names = [doc["name"] for doc in all_docs]
        
        # If no documents exist
        if not doc_names:
            return {
                "answer": "No documents found in database. Please upload documents first.",
                "sources": [],
                "context": None,
                "searched_docs": []
            }

        # 1. Retrieve relevant chunks
        if len(doc_names) == 1:
            chunks = self.retrieve_single_document(doc_names[0], question, user_id, n_results)
        else:
            chunks = self.retrieve_multiple_documents(doc_names, question, user_id, n_results)

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
    
    def _handle_conversational_query(self, query: str) -> str | None:
        """
        Handle conversational/meta queries without RAG.
        Returns response if conversational, None if needs RAG.
        """
        query_lower = query.lower().strip()
        
        # Greetings
        greetings = ["hi", "hello", "hi there", "hey", "good morning", "good afternoon", "good evening"]
        if any(query_lower.startswith(g) for g in greetings) and len(query_lower.split()) <= 3:
            return "Hello! I'm FinQuery, your financial document assistant. I can help you find information in your uploaded documents. What would you like to know?"
        
        # Identity questions
        identity_keywords = [
            "what are you", "who are you", "what is finquery", 
            "tell me about yourself", "what do you do", "what can you do",
            "how do you work", "what's your purpose"
        ]
        if any(keyword in query_lower for keyword in identity_keywords):
            return "I'm FinQuery, an AI assistant that helps you analyze financial documents. Upload PDFs of reports, statements, or other financial documents, and I'll answer questions about them using the exact information from those documents. I can help you find specific numbers, summarize sections, and explain financial data—all with source citations so you know exactly where the information comes from."
        
        # Capability questions
        capability_keywords = ["how does this work", "how to use", "help me", "what can i ask", "how do i use this"]
        if any(keyword in query_lower for keyword in capability_keywords):
            return "Here's how to use FinQuery:\n\n1. Upload financial documents (PDFs) using the sidebar\n2. Optionally select specific documents to search (or I'll search all)\n3. Ask questions about the content - numbers, dates, trends, summaries, etc.\n4. I'll provide answers with page citations so you can verify\n\nTry asking things like:\n- 'What was the revenue in Q3?'\n- 'Summarize the key financial metrics'\n- 'What were the operating expenses?'"
        
        # Thanks/gratitude
        thanks_keywords = ["thank you", "thanks", "thx", "appreciate", "arigato"]
        if any(keyword in query_lower for keyword in thanks_keywords) and len(query_lower.split()) <= 5:
            return "You're welcome! Let me know if you have any other questions about your documents."
        
        # Goodbyes
        goodbye_keywords = ["bye", "goodbye", "see you", "exit", "quit"]
        if any(keyword in query_lower for keyword in goodbye_keywords) and len(query_lower.split()) <= 3:
            return "Goodbye! Feel free to come back anytime you need to analyze financial documents."
        
        # Not a conversational query - needs RAG
        return None