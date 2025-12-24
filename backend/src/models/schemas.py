from pydantic import BaseModel, Field

class QueryRequest(BaseModel):
    question: str = Field(..., min_length=3)
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
