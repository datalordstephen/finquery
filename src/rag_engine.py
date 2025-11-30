from vector_store import query_collection   

def retrieve_context(collection, query: str, n: int = 3) -> tuple[str, list]:
    """
    Helper function to get context string and sources from the DB.
    """    
    results = query_collection(collection, query, n_results=n)
    
    # Handle case where no results are found
    if not results['documents'][0]:
        return "", []

    context_list = results['documents'][0]
    sources_list = results['metadatas'][0]
    
    # Join chunks with a separator
    context_str = "\n\n---\n\n".join(context_list)
    return context_str, sources_list

def generate_answer(client, context: str, query: str) -> str:
    """
    Pure generation logic. Takes client, context, and query -> returns answer string.
    """
    if not context:
        return "I couldn't find any relevant information in the documents."

    system_prompt = """You are a financial analyst. Use the provided context to answer the user's question. 
    If the answer involves numbers from a table, cite the row/column. 
    Always mention the source page number."""
    
    user_prompt = f"Context:\n{context}\n\nQuestion: {query}"

    response = client.chat.completions.create(
        model="gpt-3.5-turbo", 
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0
    )
    
    return response.choices[0].message.content