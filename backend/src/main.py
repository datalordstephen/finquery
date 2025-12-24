from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from together import Together

from .services.ingest import process_pdf
from .services.vector_store import add_documents, list_all_documents, delete_document_collection, get_collection_stats
from .services.rag_engine import RAGEngine
from .models.schemas import *

import os
import shutil
from dotenv import load_dotenv  

# Disable tokenizer parallelism to avoid fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize FastAPI
app = FastAPI(
    title="FinQuery API",
    description="Multi-Document Financial Q&A System",
    version="2.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

load_dotenv()   

# Initialize together and RAG engine (lazy loading)
together_client = Together()
rag_engine: RAGEngine | None = None

def get_rag_engine():
    """Lazy initialization of RAG engine. (when needed)"""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine(together_client, use_hybrid=True)
    return rag_engine

######################### API Endpoints #########################

# <---------------------- GET requests ---------------------->
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FinQuery Multi-Document API",
        "version": "2.0.0"
    }

@app.get("/documents", response_model=DocumentsListResponse)
async def list_documents():
    """
    List all uploaded documents.
    """
    if not os.path.exists("./chroma_db"):
        return DocumentsListResponse(documents=[], total_documents=0)
    
    docs = list_all_documents()
    
    return DocumentsListResponse(
        documents=[DocumentInfo(**doc) for doc in docs],
        total_documents=len(docs)
    )

@app.get("/documents/{doc_name}")
async def get_document_stats(doc_name: str):
    """
    Get statistics for a specific document.
    """
    stats = get_collection_stats(doc_name)
    
    if not stats["exists"]:
        raise HTTPException(404, f"Document '{doc_name}' not found")
    
    return stats


# <---------------------- POST requests ---------------------->
@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...)):
    """
    Upload and process a PDF document.
    Each document gets its own collection.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    temp_path = f"./temp_{file.filename}"
    
    # Save file temporarily and process it
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # process pdf
        chunks, no_of_pages = process_pdf(temp_path)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No content extracted from PDF")
        
        # add to specific collection
        result = add_documents(chunks, file.filename, no_of_pages)
        
        # clear cache in for future re-uploads with same filename
        engine = get_rag_engine()
        if file.filename in engine.bm25_cache:
            del engine.bm25_cache[file.filename]
        
        # Cleanup
        os.remove(temp_path)
        
        return UploadResponse(
            filename = file.filename,
            message=f"Successfully processed {file.filename}",
            pages=no_of_pages,
            **result
        )
    
    # Cleanup on error
    except Exception as e:
        import traceback
        traceback.print_exc()

        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Ask a question about one or more documents.
    
    Examples:
    - Query all documents: {"question": "What was the revenue?"}
    - Query specific doc: {"question": "...", "document_names": ["report.pdf"]}
    - Query multiple docs: {"question": "...", "document_names": ["q1.pdf", "q2.pdf"]}
    """
    # Check if any documents exist
    all_docs = list_all_documents()
    if not all_docs:
        raise HTTPException(400, "No documents in database. Please upload documents first.")
    
    try:
        engine = get_rag_engine()
        
        # Run RAG pipeline
        result = engine.query(
            question=request.question,
            doc_names=request.document_names,
            n_results=request.n_results
        )
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            question=request.question,
            searched_docs=result["searched_docs"]
        )
    
    except Exception as e:
        raise HTTPException(500, f"Query error: {str(e)}")


# <---------------------- DELETE requests ---------------------->
@app.delete("/documents/{doc_name}")
async def delete_document(doc_name: str):
    """
    Delete a specific document and its collection.
    """
    success = delete_document_collection(doc_name)
    
    if not success:
        raise HTTPException(404, f"Document '{doc_name}' not found")
    
    # Clear from BM25 cache
    engine = get_rag_engine()
    if doc_name in engine.bm25_cache:
        del engine.bm25_cache[doc_name]
    
    return {"message": f"Document '{doc_name}' deleted successfully"}

@app.delete("/documents")
async def clear_all_documents():
    """
    Clear all documents from the database.
    """
    try:
        if os.path.exists("./chroma_db"):
            shutil.rmtree("./chroma_db")
        
        # Reset RAG engine
        global rag_engine
        rag_engine = None
        
        return {"message": "All documents cleared successfully"}
    
    except Exception as e:
        raise HTTPException(500, f"Clear error: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)