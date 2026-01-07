from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from together import Together

from .services.auth import create_access_token, get_current_user, get_current_user_optional, get_password_hash, verify_password
from .services.ingest import process_pdf
from .services.vector_store import add_documents, list_all_documents, delete_document_collection, get_collection_stats
from .services.rag_engine import RAGEngine
from .models.schemas import *
from .models.user import User
from .database import get_db, engine, Base
from sqlalchemy.orm import Session

from datetime import timedelta, datetime
import os
import shutil
from dotenv import load_dotenv  

# Create database tables (if relying on this instead of alembic for initial dev)
Base.metadata.create_all(bind=engine)

# Disable tokenizer parallelism to avoid fork warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Initialize FastAPI
app = FastAPI(
    title="FinQuery API",
    description="Multi-Document Financial Q&A System with User Management",
    version="3.0.0"
)

# Initialize users_db removal
# users_db = {}

# Get allowed origins from environment variable
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173"
).split(",")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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

@app.get("/me", response_model=UserResponse)
async def get_current_user_info(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get current user information.
    """
    user = db.query(User).filter(User.email == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    
    return {
        "email": user.email,
        "created_at": user.created_at
    }

@app.get("/documents", response_model=DocumentsListResponse)
async def list_documents(user_id: str = Depends(get_current_user)):
    """
    List all uploaded documents (for current user)
    """
    if not os.path.exists("./chroma_db"):
        return DocumentsListResponse(documents=[], total_documents=0)
    
    docs = list_all_documents(user_id)
    
    return DocumentsListResponse(
        documents=[DocumentInfo(**doc) for doc in docs],
        total_documents=len(docs)
    )

@app.get("/documents/{doc_name}")
async def get_document_stats(doc_name: str, user_id: str = Depends(get_current_user)):
    """
    Get statistics for a specific document.
    """
    stats = get_collection_stats(doc_name, user_id)
    
    if not stats["exists"]:
        raise HTTPException(404, f"Document '{doc_name}' not found")
    
    return stats


# <---------------------- POST requests ---------------------->
@app.post("/register", response_model=Token)
async def register(user: UserRegister, db: Session = Depends(get_db)):
    """
    Register a new user.
    """
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(400, "Email already registered")
    
    hashed_password = get_password_hash(user.password)
    new_user = User(
        email=user.email,
        hashed_password=hashed_password,
        created_at=datetime.utcnow()
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    access_token = create_access_token(
        data={"sub": new_user.email},
        expires_delta=timedelta(minutes=30)
    )
    
    print(f"✓ New user registered: {new_user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": new_user.email
    }

@app.post("/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    """
    Login existing user.
    """
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user:
        raise HTTPException(401, "Invalid email or password")
    
    if not verify_password(user.password, db_user.hashed_password):
        raise HTTPException(401, "Invalid email or password")
    
    access_token = create_access_token(
        data={"sub": db_user.email},
        expires_delta=timedelta(minutes=30)
    )
    
    print(f"✓ User logged in: {db_user.email}")
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": db_user.email
    }

@app.post("/upload", response_model=UploadResponse)
async def upload_document(file: UploadFile = File(...), user_id: str = Depends(get_current_user)):
    """
    Upload and process a PDF document (for current user)
    Each document gets its own collection.
    """
    # Validate file type
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    temp_path = f"./{file.filename}"
    
    # Save file temporarily and process it
    try:
        with open(temp_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # process pdf
        chunks, no_of_pages = process_pdf(together_client, temp_path)
        
        if not chunks:
            raise HTTPException(status_code=400, detail="No content extracted from PDF")
        
        # add to specific collection for current user
        result = add_documents(chunks, file.filename, user_id, no_of_pages)
        
        # clear cache in for future re-uploads with same filename
        engine = get_rag_engine()
        cache_key = f"{user_id}_{file.filename}"
        if cache_key in engine.bm25_cache:
            del engine.bm25_cache[cache_key]
        
        # Cleanup
        os.remove(temp_path)

        print(f"✓ Document uploaded: {file.filename} (user: {user_id})")
        
        return UploadResponse(
            filename = file.filename,
            message=f"Successfully processed {file.filename}",
            pages=no_of_pages,
            **result
        )
    
    # Cleanup on error
    except Exception as e:

        if os.path.exists(temp_path):
            os.remove(temp_path)
        raise HTTPException(status_code=500, detail=f"Processing error: {str(e)}")

@app.post("/query", response_model=QueryResponse)
async def query_documents(request: QueryRequest, user_id: str = Depends(get_current_user)):
    """
    Ask a question about one or more documents.
    """
    
    try:
        engine = get_rag_engine()
        
        # Run RAG pipeline
        result = engine.query(
            question=request.question,
            doc_names=request.document_names,
            n_results=request.n_results,
            user_id=user_id
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
async def delete_document(doc_name: str, user_id: str = Depends(get_current_user)):
    """
    Delete a specific document and its collection.
    """
    success = delete_document_collection(doc_name, user_id)
    
    if not success:
        raise HTTPException(404, f"Document '{doc_name}' not found")
    
    # Clear from BM25 cache
    engine = get_rag_engine()
    cache_key = f"{user_id}_{doc_name}"
    if cache_key in engine.bm25_cache:
        del engine.bm25_cache[cache_key]
        print(f"✓ Delected {doc_name} BM25 cache (user: {user_id})")
    
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