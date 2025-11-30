import pdfplumber
import pandas as pd


def process_pdf(pdf_path: str) -> list  :
    """
    Extracts both text and tables from a PDF. 
    Tables are converted to Markdown to preserve structure for the LLM.
    """
    chunks = []
    
    # open pdf and iterate through pages
    with pdfplumber.open(pdf_path) as pdf:
        for page_num, page in enumerate(pdf.pages):
            # check for tables
            tables = page.extract_tables()
            for table in tables:
                # Filter out tiny/empty tables
                if not table or len(table) < 2: 
                    continue
                
                # Convert to Markdown (LLMs understand this best)
                # We assume first row is header. 
                try:
                    df = pd.DataFrame(table[1:], columns=table[0])
                    df = df.fillna("") 
                    markdown_table = df.to_markdown(index=False)
                    
                    chunks.append({
                        "content": f"Table on Page {page_num + 1}:\n{markdown_table}",
                        "metadata": {"page": page_num + 1, "type": "table", "source": pdf_path}
                    })
                except Exception as e:
                    print(f"Skipping malformed table on page {page_num}: {e}")

            # 2. Extract Text (simple extraction for now)
            # In a real prod system, you might mask the table areas to avoid duplication
            text = page.extract_text()
            if text:
                paragraphs = text.split('\n\n')
                for p in paragraphs:
                    # filter headers/footers
                    if len(p.strip()) > 50:  
                        chunks.append({
                            "content": p.strip(),
                            "metadata": {"page": page_num + 1, "type": "text", "source": pdf_path}
                        })
                        
    return chunks