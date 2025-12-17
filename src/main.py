import os
from dotenv import load_dotenv
from together import Together
from document_processor import process_pdf
from vector_store import get_chroma_collection, add_documents
from rag_engine import retrieve_context, generate_answer

load_dotenv()

together_client = Together()

PDF_PATH = "assets/2023_Annual_Report.pdf" 

# setup openai and chroma db
collection = get_chroma_collection()

# process and add documents if needed
if os.path.exists(PDF_PATH):
    print(f"Processing {PDF_PATH}...")
    chunks = process_pdf(PDF_PATH, n_pages=10)
    add_documents(collection, chunks)
else:
    print("No PDF found. Using existing database if available.")

# # 3. Interactive Loop
# print("\n--- Financial RAG System (Functional) Ready ---")
# while True:
#     query = input("\nAsk a question (or 'exit'): ")
#     if query.lower() == 'exit':
#         break
    
#     # Step A: Get Context (Pass the collection)
#     context_str, sources = retrieve_context(collection, query)
    
#     # Step B: Generate Answer (Pass the client and context)
#     answer = generate_answer(openai_client, context_str, query)
    
#     print("\nAnswer:")
#     print(answer)
    
#     if sources:
#         print("\nSources:")
#         for source in sources:
#             print(f"- Page {source['page']} ({source['type']})")


