import os
from google import genai
from google.genai import types
from dotenv import load_dotenv

from rag.pdf_reader import extract_text
from rag.chunker import chunk_text
from rag.embedder import create_embedding
from rag.retriever import store_chunks, search_chunks

# Load environment variables
load_dotenv()

# Initialize Google GenAI Client
api_key = os.getenv("GEMINI_API_KEY")
client = None
if api_key:
    client = genai.Client(api_key=api_key)

def ingest_pdf(pdf_path):
    """
    Runs the full end-to-end ingestion flow:
    PDF Path -> Extract Text -> Chunk Text -> Create Embeddings -> Store in ChromaDB
    
    Args:
        pdf_path (str): File path to the PDF to ingest.
        
    Returns:
        int: The number of chunks successfully ingested.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF document not found at {pdf_path}")
        
    # 1. Extract text from PDF
    text = extract_text(pdf_path)
    if not text.strip():
        raise ValueError("Extracted text is empty.")
        
    # 2. Chunk text intelligently
    chunks = chunk_text(text)
    if not chunks:
        raise ValueError("Chunking generated 0 chunks.")
        
    # 3. Create Gemini embeddings for each chunk
    embeddings = []
    for chunk in chunks:
        emb = create_embedding(chunk)
        embeddings.append(emb)
        
    # 4. Prepare metadata (store the source file name)
    source_filename = os.path.basename(pdf_path)
    metadatas = [{"source": source_filename} for _ in chunks]
    
    # 5. Store embeddings and text chunks in ChromaDB
    store_chunks(chunks, embeddings, metadatas=metadatas)
    
    return len(chunks)

def is_chunk_relevant(chunk_text, query):
    """
    Checks if the retrieved chunk actually contains query-relevant concepts/keywords.
    This serves as a hallucination-safe guardrail before sending text to LLM.
    """
    query_lower = query.lower()
    chunk_lower = chunk_text.lower()
    
    # Map keywords in user query to domain synonyms that should be in the chunk
    keyword_synonyms = {
        "nitrogen": ["nitrogen", " n ", "urea", "specification"],
        "phosphate": ["phosphate", "phosphorus", "p2o5", "specification", "superphosphate"],
        "potassium": ["potassium", "potash", " k ", "specification", "chloride"],
        "moisture": ["moisture", "water", "humidity", "dry weight"],
        "delivery": ["delivery", "days", "timeline", "schedule", "shipment"],
        "packaging": ["packaging", "bag", "package", "layer"],
        "urea": ["urea", "nitrogen", "fertilizer", "specification"]
    }
    
    keywords_to_check = []
    for key, synonyms in keyword_synonyms.items():
        if key in query_lower:
            keywords_to_check.append(synonyms)
            
    # Generic word validation if no domain keywords matched
    if not keywords_to_check:
        words = [w for w in query_lower.split() if len(w) > 4]
        # Ignore common query stop words
        stop_words = {"what", "where", "which", "there", "their", "about", "would", "should"}
        words = [w for w in words if w not in stop_words]
        if not words:
            return True
        return any(word in chunk_lower for word in words)
        
    # Chunk must contain at least one synonym for each query concept identified
    for synonyms in keywords_to_check:
        if not any(syn in chunk_lower for syn in synonyms):
            return False
            
    return True

def retrieve_context(query):
    """
    Performs semantic search on the query to retrieve top context chunks.
    
    Args:
        query (str): The search query.
        
    Returns:
        str: Concatenated context chunks with citations (chunk ID and source metadata).
    """
    # Retrieve top 5 semantic chunks
    results = search_chunks(query, n_results=5)
    if not results:
        return ""
        
    # Format chunks with citation details and filter by keyword relevance
    formatted_chunks = []
    for item in results:
        text = item.get("text", "")
        
        # Filter out chunks that do not pass relevance check
        if not is_chunk_relevant(text, query):
            continue
            
        chunk_id = item.get("chunk_id", "unknown")
        meta = item.get("metadata", {})
        source = meta.get("source", "tender_document")
        
        formatted_chunks.append(
            f"[Chunk ID: {chunk_id} | Source: {source}]\n{text}"
        )
        
    return "\n\n---\n\n".join(formatted_chunks)

def query_pipeline(query):
    """
    Retrieves semantically relevant clauses and queries the model using context-grounded prompt engineering.
    
    Args:
        query (str): The query question.
        
    Returns:
        str: Grounded response or strict fallbacks ('INSUFFICIENT CONTEXT' or 'NO RELEVANT RULE FOUND').
    """
    global client
    if not client:
        load_dotenv()
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            return "Error: GEMINI_API_KEY is not set."
        client = genai.Client(api_key=key)

    # 1. Retrieve context
    context = retrieve_context(query)
    
    # Null handling: If no relevant chunk exists
    if not context or not context.strip():
        return "NO RELEVANT RULE FOUND"
        
    # 2. Construct the strict prompt enforcing context-only answering
    system_instruction = (
        "You are a strict agricultural procurement auditor.\n"
        "ONLY use the provided context to answer the question.\n"
        "If the information needed to answer the question is missing from the context, "
        "you MUST return exactly: 'INSUFFICIENT CONTEXT'\n"
        "Do NOT invent rules. Do NOT guess values. Do NOT hallucinate."
    )
    
    prompt = (
        f"{system_instruction}\n\n"
        f"--- CONTEXT START ---\n"
        f"{context}\n"
        f"--- CONTEXT END ---\n\n"
        f"USER QUESTION:\n{query}\n\n"
        f"Strict auditor grounded response:"
    )
    
    try:
        # Call Gemini 2.5 Flash with low temperature
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.1
            )
        )
        
        ans = response.text
        if not ans or not ans.strip():
            return "INSUFFICIENT CONTEXT"
            
        return ans.strip()
    except Exception as e:
        return f"Error during model generation: {str(e)}"
