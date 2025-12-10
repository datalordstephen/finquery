import pdfplumber
import pandas as pd
from langchain_text_splitters import RecursiveCharacterTextSplitter

# using langchain's text splitter for chunking texts
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=len, 
    add_start_index=True
)

def chunk_pdf(pdf_path: str, n_pages: int = None) -> list  :
    """
    Extracts both text and tables from a PDF. 
    Tables are converted to Markdown and saved as a chunk to preserve structure for the LLM.
    Text is chunked using langchain's text splitter.
    """
    chunks = []
    
    # open pdf and iterate through pages up to n_pages
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            if n_pages:
                if page_num >= n_pages:
                    break
            
            # process tables as markdowns and save as single chunk (best for llms)
            tables = page.extract_tables()
            print(f"Found: {len(tables)} tables")
            print(f"Found: {page.find_tables()} tables")
            for i, table in enumerate(tables):
                if not table or len(table) < 2: 
                    continue
                
                try:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    df = df.fillna("") 
                    markdown_table = df.to_markdown(index=False)
                    
                    chunks.append({
                        "content": f"Table {i+1} on Page {page_num + 1}:\n{markdown_table}",
                        "metadata": {
                            "table_no": i, 
                            "page": page_num + 1, 
                            "type": "table", 
                            "source": pdf_path
                    }})
                except Exception as e:
                    print(f"Skipping malformed table on page {page_num}: {e}")

            # chunk text with langchain
            text = page.extract_text()
            if text:
                text_splits = TEXT_SPLITTER.split_text(text)
                text_chunks = [
                    {
                        "content": p.strip(),
                        "metadata": {
                            "chunk_id": id, 
                            "page": page_num + 1, 
                            "type": "text", 
                            "source": pdf_path}
                    }
                    for id, p in enumerate(text_splits)
                ]
                chunks.extend(text_chunks)
    return chunks

