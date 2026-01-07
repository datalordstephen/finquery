from pydantic import BaseModel, Field
from datetime import datetime

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=2)
    document_names: list[str] | None = Field(None, description="List of docs to search. If null, searches all docs.")
    n_results: int = Field(default=5, ge=1, le=20)

class QueryResponse(BaseModel):
    answer: str
    sources: list[dict]
    question: str
    searched_docs: list[str]

class UploadResponse(BaseModel):
    filename: str
    collection_name: str
    pages: int
    total_docs: int
    message: str

class DocumentInfo(BaseModel):
    name: str
    count: int
    pages: int | None

class DocumentsListResponse(BaseModel):
    documents: list[DocumentInfo]
    total_documents: int

class UserRegister(BaseModel):
    email: str = Field(..., min_length=3, pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
    password: str = Field(..., min_length=6)

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    email: str

class UserResponse(BaseModel):
    email: str
    created_at: datetime
