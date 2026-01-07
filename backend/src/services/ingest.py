import pymupdf
from langchain_text_splitters import RecursiveCharacterTextSplitter
import os
from .process_tables import enhance_table_with_context, extract_tables_with_camelot

# Simple splitter config
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len
)


def process_pdf(llm_client, pdf_path: str) -> list[dict]:
    """
    Process PDF with table-aware chunking.
    
    Strategy:
    1. Extract tables with Camelot (enhanced with LLM context)
    2. Extract text with PyMuPDF (excluding table areas)
    3. Return both as separate chunks

    Args:
        llm_client: Together API client
        pdf_path: path to uploaded pdf
    """
    chunks = []
    doc_name = os.path.basename(pdf_path)

    doc = pymupdf.open(pdf_path)
    pages = len(doc)
    
    print(f"\n{'='*60}")
    print(f"Processing: {doc_name}")
    print(f"{'='*60}")
    print(f"Pages: {pages}")

    # Extract tables with Camelot
    tables_by_page = extract_tables_with_camelot(pdf_path)
    
    for page_num in range(pages):
        page = doc[page_num]
        page_text = page.get_text("text")
        actual_page_num = page_num + 1
        
        # Skip empty pages
        if not page_text.strip():
            continue

        # Process tables on this page (if any exists)
        if actual_page_num in tables_by_page:
            for table_idx, table_md in enumerate(tables_by_page[actual_page_num]):
                # Enhance table with LLM context
                enhanced_table = enhance_table_with_context(
                    llm_client,
                    table_md,
                    page_text,
                    actual_page_num
                )
                
                doc_id = f"{doc_name}::page_{actual_page_num}::table_{table_idx + 1}"
                
                chunks.append({
                    "content": enhanced_table,
                    "metadata": {
                        "type": "table",
                        "page": actual_page_num,
                        "source": pdf_path,
                        "doc_id": doc_id,
                        "table_num": table_idx + 1
                    }
                })
        
        # Split page text into chunks
        page_chunks = TEXT_SPLITTER.split_text(page_text)
        
        # Add each chunk with metadata
        for chunk_idx, chunk_text in enumerate(page_chunks):
            if not chunk_text.strip():
                continue
            
            doc_id = f"{doc_name}::page_{actual_page_num}::chunk_{chunk_idx}"
            
            chunk = {
                "content": chunk_text.strip(),
                "metadata": {
                    "type": "text",
                    "page": actual_page_num,
                    "source": pdf_path,
                    "doc_id": doc_id
                }
            }
            chunks.append(chunk)

    doc.close()

    table_count = sum(1 for c in chunks if c["metadata"]["type"] == "table")
    text_count = len(chunks) - table_count
    
    print(f"✓ Extracted {len(chunks)} chunks: ({text_count} text, {table_count} tables)")
    print(f"{'='*60}\n")
    
    return chunks, pages