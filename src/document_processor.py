from annotated_types import Len
import pymupdf4llm
import pymupdf
import re
from langchain_text_splitters import RecursiveCharacterTextSplitter
import re
import statistics

# splitter config
TEXT_SPLITTER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
    length_function=Len
)

# for regex
NUMBER_PATTERN = re.compile(r"\d")
LOWER_START_RE = re.compile(r"^[a-z]")

# <----- helper functions ---------->
def extract_page_texts(pdf_path: str) -> dict[int, str]:
    """
    Extract raw text per page using PyMuPDF.
    This gives us reliable page numbers.
    """
    doc = pymupdf.open(pdf_path)
    page_texts = {}

    for i, page in enumerate(doc):
        page_texts[i + 1] = page.get_text("text")

    return page_texts

def extract_markdown(pdf_path: str) -> str:
    """
    Extract full-document Markdown using pymupdf4llm.
    """
    return pymupdf4llm.to_markdown(pdf_path)

# <----- logic to split pdf in markdown into "blocks" ---------->
def split_blocks(markdown: str) -> list[str]:
    """
    Split markdown into logical blocks separated by blank lines.
    """
    return [b.strip() for b in markdown.split("\n\n\n") if b.strip()]


# <----- logic to determine which "block" contains a table  ---------->
def is_prose_like(block: str) -> bool:
    """
    Detects flowing narrative text broken by layout line-wrapping.
    Acts as a veto before layout-based table detection.
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if len(lines) < 3:
        return False

    flowing_breaks = 0
    verb_hits = 0

    for i in range(len(lines) - 1):
        # sentence continues across line break
        if (
            not re.search(r"[.:;]$", lines[i]) and
            LOWER_START_RE.match(lines[i + 1])
        ):
            flowing_breaks += 1

    for w in re.findall(r"\b\w+\b", block.lower()):
        if (
            w.endswith("ed") or
            w.endswith("ing") or
            w in {"was", "were", "has", "may", "is", "approved", "commenced"}
        ):
            verb_hits += 1

    return flowing_breaks >= 2 or verb_hits >= 3


def passes_table_layout_heuristics(block: str) -> bool:
    """
    Pure layout-based table detector.
    """
    lines = [l.strip() for l in block.splitlines() if l.strip()]
    if len(lines) < 3:
        return False

    # Column inference via multi-space splits
    column_counts = []
    numeric_lines = 0

    for line in lines:
        cols = re.split(r"\s{2,}", line)
        column_counts.append(len(cols))
        if NUMBER_PATTERN.search(line):
            numeric_lines += 1

    # Column consistency (allow header variance)
    if len(set(column_counts)) > 2:
        return False

    # Numbers must appear on most rows
    if numeric_lines < max(3, int(0.6 * len(lines))):
        return False

    # Line length consistency (tables are regular)
    lengths = [len(l) for l in lines]
    if statistics.pstdev(lengths) > 0.5 * statistics.mean(lengths):
        return False

    return True


def is_table_block(block: str) -> bool:
    """
    Final table classifier.
    """
    # Prose always wins
    if is_prose_like(block):
        return False

    return passes_table_layout_heuristics(block)

# <----- end logic ---------->

# <----- match page -> page number ---------->
def find_block_page(block: str, page_texts: dict[int, str]) -> int | None:
    """
    Match a markdown block to its source page using numeric anchors.
    """
    anchors = re.findall(
        r"\b(?:\d{4}|\$?\d[\d,]*\.?\d*)\b",
        block
    )

    for page_num, text in page_texts.items():
        score = sum(anchor in text for anchor in anchors[:10])
        if score >= 3:
            return page_num

    return None


def normalize_table(table_block: str) -> str:
    """
    Convert space-aligned table into explicit Markdown table.
    """
    rows = [
        re.split(r"\s{2,}", line.strip())
        for line in table_block.splitlines()
    ]

    max_cols = max(len(r) for r in rows)
    rows = [r + [""] * (max_cols - len(r)) for r in rows]

    header = rows[0]
    body = rows[1:]

    md = []
    md.append("| " + " | ".join(header) + " |")
    md.append("| " + " | ".join(["---"] * max_cols) + " |")

    for row in body:
        md.append("| " + " | ".join(row) + " |")

    return "\n".join(md)

