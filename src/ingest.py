from .document_processor import *

def process_pdf(pdf_path: str) -> list[dict]:
    """
    End-to-end PDF processor:
    - Extracts Markdown via pymupdf4llm
    - Detects tables
    - Recovers page numbers
    - Chunks narrative text
    """
    chunks = []

    page_texts = extract_page_texts(pdf_path)
    markdown = extract_markdown(pdf_path)
    blocks = split_blocks(markdown)

    for block in blocks:
        page = find_block_page(block, page_texts)

        # ---------- TABLE ----------
        if is_table_block(block):
            chunks.append({
                "content": normalize_table(block),
                "metadata": {
                    "type": "table",
                    "page": page,
                    "source": pdf_path,
                }
            })

        # ---------- TEXT ----------
        else:
            splits = TEXT_SPLITTER.split_text(block)
            for i, split in enumerate(splits):
                chunks.append({
                    "content": split.strip(),
                    "metadata": {
                        "type": "text",
                        "page": page,
                        "chunk": i,
                        "source": pdf_path,
                    }
                })

    return chunks