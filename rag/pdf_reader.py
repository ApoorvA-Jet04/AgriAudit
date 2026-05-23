import os
import fitz  # PyMuPDF

def extract_text(pdf_path):
    """
    Extracts all text from a given PDF file path using PyMuPDF (fitz).
    
    Args:
        pdf_path (str): Absolute or relative path to the PDF file.
        
    Returns:
        str: Concatenated, clean text extracted from all pages.
    """
    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")
        
    text_content = []
    try:
        # Open PDF document
        doc = fitz.open(pdf_path)
        
        if len(doc) == 0:
            doc.close()
            raise ValueError(f"The PDF file at {pdf_path} is invalid or has 0 pages.")
            
        # Iterate through pages and extract text
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            if page_text:
                text_content.append(page_text)
                
        doc.close()
    except Exception as e:
        if isinstance(e, ValueError):
            raise e
        raise RuntimeError(f"Error reading PDF at {pdf_path}. It might be corrupted or invalid: {str(e)}")
        
    # Join page texts with a space or newline
    clean_text = "\n".join(text_content).strip()
    
    if not clean_text:
        raise ValueError(
            f"No text content could be extracted from PDF at {pdf_path}. "
            "This PDF might be scanned (image-only) and requires OCR, or is invalid."
        )
        
    print("EXTRACTED TEXT:")
    print(clean_text[:3000])
    print("-" * 60)
    
    return clean_text
