import os
import fitz  # PyMuPDF
from rag.rag_pipeline import ingest_pdf, query_pipeline, retrieve_context

def create_sample_pdf(pdf_path):
    """
    Creates a sample agricultural tender PDF with chemical specifications
    to verify text extraction, chunking, embedding, and semantic retrieval.
    """
    print(f"[*] Creating sample PDF at: {pdf_path}")
    doc = fitz.open()
    page = doc.new_page()
    
    text = (
        "AGRICULTURAL TENDER DOCUMENT: FERTILIZER AND SOIL AMENDMENTS\n\n"
        "1. GENERAL GUIDELINES\n"
        "This tender outlines procurement requirements for agricultural inputs for the crop cycle.\n\n"
        "2. TECHNICAL CHEMICAL SPECIFICATIONS\n"
        "2.1 Urea Chemical Specifications:\n"
        "The supplier must guarantee standard agricultural-grade granulated urea. "
        "The nitrogen percentage requirement is strictly set to a minimum of 46.0% dry weight. "
        "Any shipment falling below 46.0% nitrogen will be rejected. Moisture content must not exceed 0.5%.\n\n"
        "2.2 Superphosphate Specifications:\n"
        "Phosphorus pentoxide (P2O5) must represent at least 18.0% of the fertilizer by weight. "
        "Granule size must be between 1mm and 4mm.\n\n"
        "3. LOGISTICS AND PACKAGING\n"
        "Fertilizers must be packaged in double-layered 50kg bags. Delivery must occur within 45 days of award."
    )
    
    # Insert textbox inside page
    rect = fitz.Rect(50, 50, 550, 750)
    page.insert_textbox(rect, text, fontsize=11, fontname="helv")
    doc.save(pdf_path)
    doc.close()
    print("[+] Sample PDF created successfully.")

def main():
    # Ensure the uploads directory exists
    os.makedirs("uploads", exist_ok=True)
    
    pdf_path = os.path.join("uploads", "sample_tender.pdf")
    
    # Dynamically build sample PDF if not present
    if not os.path.exists(pdf_path):
        create_sample_pdf(pdf_path)
        
    print("\n[1] Starting Ingestion of PDF...")
    try:
        num_chunks = ingest_pdf(pdf_path)
        print(f"[Success] Ingested {num_chunks} chunks into ChromaDB 'tender_rules' collection.")
    except Exception as e:
        print(f"[Error] Ingestion failed: {e}")
        return
        
    # Test Question 1: In-context request
    query = "What is the nitrogen percentage requirement?"
    print(f"\n[2] Performing Semantic Retrieval for Query: '{query}'")
    
    context = retrieve_context(query)
    print("\n--- RETRIEVED CHUNKS ---")
    print(context if context else "No relevant context found.")
    print("------------------------")
    
    print(f"\n[3] Querying RAG Pipeline with Gemini Answering...")
    answer = query_pipeline(query)
    print("\n--- GEMINI ANSWER ---")
    print(answer)
    print("---------------------")
    
    # Test Question 2: Out-of-context query (retrieves sections but has no answer details)
    out_of_context_query = "What is the price per ton of urea?"
    print(f"\n[4] Testing Hallucination Prevention for Query: '{out_of_context_query}'")
    print("Expectation: System should respond with 'INSUFFICIENT CONTEXT' (since pricing is not in the document).")
    
    bad_answer = query_pipeline(out_of_context_query)
    print("\n--- GEMINI ANSWER ---")
    print(bad_answer)
    print("---------------------")
    
    # Test Question 3: Completely unrelated query (retrieves no relevant context)
    unrelated_query = "What is the capital of France?"
    print(f"\n[5] Testing Full Context Rejection for Query: '{unrelated_query}'")
    print("Expectation: System should respond with 'NO RELEVANT RULE FOUND' (due to keyword filtering).")
    
    unrelated_answer = query_pipeline(unrelated_query)
    print("\n--- GEMINI ANSWER ---")
    print(unrelated_answer)
    print("---------------------")

if __name__ == "__main__":
    main()
