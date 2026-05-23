import re

def chunk_text(text, chunk_size=850, overlap=100):
    """
    Splits extracted text into chunks of size between 700 and 1000 characters,
    with an overlap of 100 characters to preserve semantic continuity.
    Avoids empty chunks and preserves sentence/word boundaries.
    
    Args:
        text (str): The full text to split.
        chunk_size (int): Target chunk size in characters (default 850).
        overlap (int): Number of characters to overlap between adjacent chunks (default 100).
        
    Returns:
        list: A list of text chunks (strings).
    """
    if not text or not text.strip():
        return []
        
    # Normalize whitespace to make length calculations predictable
    normalized_text = re.sub(r'\s+', ' ', text).strip()
    text_len = len(normalized_text)
    
    chunks = []
    start = 0
    
    while start < text_len:
        end = start + chunk_size
        
        # If we are near the end of the text, take the rest of the text
        if end >= text_len:
            chunk = normalized_text[start:].strip()
            if chunk:
                chunks.append(chunk)
            break
            
        # Look for sentence boundaries (., ?, !, or newline) around the end of the window
        # Search backwards up to 150 characters to keep chunk within 700-1000 chars
        boundary_idx = -1
        for i in range(end, max(start + 200, end - 150), -1):
            if normalized_text[i] in ('.', '?', '!'):
                boundary_idx = i + 1  # Include the punctuation mark
                break
                
        # If no sentence boundary is found, search backwards for a word boundary (space)
        if boundary_idx == -1:
            for i in range(end, max(start + 200, end - 80), -1):
                if normalized_text[i].isspace():
                    boundary_idx = i
                    break
                    
        # Apply the boundary index if found, otherwise cut exactly at end
        actual_end = boundary_idx if boundary_idx != -1 else end
        
        chunk = normalized_text[start:actual_end].strip()
        if chunk:
            chunks.append(chunk)
            
        # The next chunk starts at actual_end minus the overlap
        start = actual_end - overlap
        
        # Guard to prevent infinite loop (ensure we make positive progress of at least 10 chars)
        if start >= actual_end - 10:
            start = actual_end
            
    # Debugging output: Print total count and first 2 chunks
    print(f"Total chunks: {len(chunks)}")
    print("FIRST 2 CHUNKS:")
    for idx, c in enumerate(chunks[:2]):
        print(f"--- Chunk {idx+1} ---")
        print(c)
    print("-" * 60)
    
    return chunks
