import camelot

# <--------- helper functions to extract and preprocess tables --------------->
def format_table(table):
    """
    format table and convert to markdown
    """
    formatted_table = table.df.apply(lambda x: x.str.replace('\n','').str.replace('\t', ' '))
    final_table = formatted_table.rename(columns=formatted_table.iloc[0]).drop(formatted_table.index[0]).reset_index(drop=True)
    return final_table.to_markdown(index=False)

def extract_tables_with_camelot(pdf_path: str, pages: str = "all") -> dict[int, list]:
    """
    Extract tables from PDF using Camelot and converts them to markdown strings.
    Returns: {page_num: [table1_md, table2_md, ...]}
    """
    tables_by_page = {}
    
    # Try stream mode first (works for most bank statements)
    try:
        tables = camelot.read_pdf(pdf_path, pages=pages, flavor="stream", edge_tol=50, row_tol=10)
        
        for table in tables:
            page_num = table.page
            if page_num not in tables_by_page:
                tables_by_page[page_num] = []   
            
            # format table and convert to markdown
            table_markdown = format_table(table=table)
            tables_by_page[page_num].append(table_markdown)
        
        print(f"✓ Extracted {len(tables)} tables (stream mode)")
        
    except Exception as e:
        print(f"Stream mode failed: {e}")
        
        # Fallback to lattice mode (for bordered tables)
        try:
            tables = camelot.read_pdf(pdf_path, pages='all', flavor='lattice')
            
            for table in tables:
                page_num = table.page
                if page_num not in tables_by_page:
                    tables_by_page[page_num] = []
                
                table_markdown = format_table(table=table)
                tables_by_page[page_num].append(table_markdown)
            
            print(f"✓ Extracted {len(tables)} tables (lattice mode)")
            
        except Exception as e2:
            print(f"Lattice mode also failed: {e2}")
    
    return tables_by_page

def enhance_table_with_context(llm_client, table_md, page_text: str, page_num: int) -> str:
    """
    Use LLM to add semantic context to table and remove irrelevant text from extracted markdown
    """
    system_prompt = f"""
You are a data preprocessing assistant for a retrieval system operating on financial documents.

Your responsibility is to normalize tables extracted from PDFs and produce summaries of them that improves search and retrieval accuracy.

You must follow these rules strictly:

1. Generate retrieval-friendly summaries
   - Summaries must be concise (2-3 sentences).
   - Describe what the table represents, the time period, and the key dimensions (e.g., line items, years).
   - Do NOT interpret trends or provide analysis.

2. Clean structure only
   - Remove stray or duplicated text that does not belong to the table.
   - Preserve headers, row labels, and column alignment.
   - Do not add or remove rows unless they are clearly non-tabular noise.

3. Preserve factual accuracy
   - Do NOT change numeric values, dates, currencies, or units.
   - Do NOT infer missing values.
   - Do NOT recompute totals or percentages.

4. Be deterministic
   - Output must be consistent given the same input.
   - Avoid stylistic variation or commentary.

Your output will be indexed by a search system. Accuracy and consistency are more important than fluency.
"""
    
    user_prompt = f"""
You are analyzing a table extracted from a financial document.

Page number:
{page_num}

Table (markdown):
{table_md}

Surrounding text from the same page:
{page_text}

Task:
1. Write a concise, factual 2-3 sentence description of what the table represents, using the surrounding text only for context.
2. Return a cleaned version of the table with any stray or non-tabular text removed.

Return the result in the following format:

---
TABLE SUMMARY:
<summary text>

CLEANED TABLE:
<markdown table>
---
"""
    try:
        response = llm_client.chat.completions.create(
            model="meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            max_tokens=1000
        )
        
        enhanced = response.choices[0].message.content.strip()

        return enhanced
        
    except Exception as e:
        print(f"LLM enhancement failed: {e}")
        return table_md
