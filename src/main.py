from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from together import Together

from .services.ingest import process_pdf
from .services.vector_store import add_documents, get_chroma_collection
from .services.rag_engine import RAGEngine
from .models.schemas import *

from typing import Optional
import os
import shutil
from dotenv import load_dotenv


# Initialize FastAPI
app = FastAPI(
    title="FinQuery API",
    description="Financial Document Q&A System using RAG",
    version="1.0.0"
)

load_dotenv()

# Initialize Together AI client
together_client = Together(api_key=os.getenv("TOGETHER_API_KEY"))

# Initialize RAG engine (lazy loading)
rag_engine: Optional[RAGEngine] = None

def get_rag_engine():
    """Lazy initialization of RAG engine."""
    global rag_engine
    if rag_engine is None:
        rag_engine = RAGEngine(together_client, use_hybrid=True)
    return rag_engine

# API Endpoints
@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "FinQuery API",
        "version": "1.0.0"
    }

@app.get("/stats")
async def get_stats():
    """Get database statistics."""
    collection = get_chroma_collection()
    return {
        "total_documents": collection.count(),
        "collection_name": collection.name
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload and process a PDF document.
    
    Processing happens in background to avoid timeout.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    # Save file temporarily
    temp_path = f"./temp_{file.filename}"
    
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process PDF
        chunks = process_pdf(temp_path)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No content extracted from PDF")
        
        # Add to vector store
        total_docs = add_documents(chunks)
        
        # Reinitialize RAG engine to include new docs in BM25
        global rag_engine
        rag_engine = None  # Force reinitialization on next query
        
        # Cleanup
        os.remove(temp_path)
        
        return UploadResponse(
            filename=file.filename,
            chunks_added=len(chunks),
            total_docs=total_docs,
            message=f"Successfully processed {file.filename}"
        )
    
    except Exception as e:
        import traceback
        traceback.print_exc()

        # Cleanup on error
        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest):
    """
    Ask a question about uploaded documents.
    """
    # Check if database has documents
    collection = get_chroma_collection()
    if collection.count() == 0:
        raise HTTPException(
            status_code=400,
            detail="No documents in database. Please upload documents first."
        )
    
    try:
        # Get RAG engine
        engine = get_rag_engine()
        
        # Run RAG pipeline
        result = engine.query(request.question, n_results=request.n_results)
        
        return QueryResponse(
            answer=result["answer"],
            sources=result["sources"],
            question=request.question
        )
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Query error: {str(e)}")

@app.delete("/documents")
async def clear_documents():
    """Clear all documents from the database."""
    try:
        # Delete chroma_db directory
        import shutil
        if os.path.exists("./chroma_db"):
            shutil.rmtree("./chroma_db")
        
        # Reset RAG engine
        global rag_engine
        rag_engine = None
        
        return {"message": "All documents cleared successfully"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Clear error: {str(e)}")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)