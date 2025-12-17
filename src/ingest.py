from .document_processor import *
import os
from collections import defaultdict

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

    doc_name = os.path.basename(pdf_path)
    page_block_counts = defaultdict(lambda: {"text": 0, "table": 0})

    for block in blocks:
        page = find_block_page(block, page_texts)

        # ---------- TABLE ----------
        if is_table_block(block):
            table_idx = page_block_counts[page]["table"]

            doc_id = (
                    f"{doc_name}"
                    f"::page_{page}"
                    f"::table_{table_idx}"
            )

            chunks.append({
                "content": normalize_table(block),
                "metadata": {
                    "type": "table",
                    "page": page,
                    "source": pdf_path,
                    "doc_id": doc_id
                }
            })

            page_block_counts[page]["table"] += 1

        # ---------- TEXT ----------
        else:
            splits = TEXT_SPLITTER.split_text(block)
            for split in splits:
                text_idx = page_block_counts[page]["text"]

                doc_id = (
                    f"{doc_name}"
                    f"::page_{page}"
                    f"::text_{text_idx}"
                )

                chunks.append({
                    "content": split.strip(),
                    "metadata": {
                        "type": "text",
                        "page": page,
                        "source": pdf_path,
                        "doc_id": doc_id
                    }
                })

                page_block_counts[page]["text"] += 1

    return chunks