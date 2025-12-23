import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os

# Simple splitter config
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)


def process_pdf(pdf_path: str) -> list[dict]:
    """
    Simple, reliable PDF processor.
    
    Strategy:
    1. Extract text page by page (we KNOW the page number)
    2. Split each page's text into chunks
    3. Keep page metadata
    
    No fancy table detection, no markdown, just works.
    """
    doc = pymupdf.open(pdf_path)
    chunks = []
    doc_name = os.path.basename(pdf_path)
    
    print(f"\n{'='*60}")
    print(f"Processing: {doc_name}")
    print(f"{'='*60}")
    print(f"Pages: {len(doc)}")
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        page_text = page.get_text("text")
        
        # Skip empty pages
        if not page_text.strip():
            continue
        
        # Split page text into chunks
        page_chunks = TEXT_SPLITTER.split_text(page_text)
        
        # Add each chunk with metadata
        for chunk_idx, chunk_text in enumerate(page_chunks):
            if not chunk_text.strip():
                continue
            
            doc_id = f"{doc_name}::page_{page_num + 1}::chunk_{chunk_idx}"
            
            chunk = {
                "content": chunk_text.strip(),
                "metadata": {
                    "type": "text",
                    "page": page_num + 1,
                    "source": pdf_path,
                    "doc_id": doc_id
                }
            }
            chunks.append(chunk)

    print(f"✓ Extracted {len(chunks)} chunks from {len(doc)} pages")
    print(f"{'='*60}\n")
    
    doc.close()

    return chunks