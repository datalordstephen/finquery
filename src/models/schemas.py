from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    question: str
    n_results: int = 5

class QueryResponse(BaseModel):
    answer: str
    sources: list
    question: str

class UploadResponse(BaseModel):
    filename: str
    chunks_added: int
    total_docs: int
    message: str
