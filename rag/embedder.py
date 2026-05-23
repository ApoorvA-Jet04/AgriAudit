import os
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure google-generativeai API key
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

def create_embedding(text):
    """
    Generates a vector embedding for the input text using Google's models/embedding-001.
    
    Args:
        text (str): The text chunk to embed.
        
    Returns:
        list: A list of floats representing the embedding vector.
    """
    if not text or not text.strip():
        raise ValueError("Input text for embedding cannot be empty.")
        
    # Lazy configuration check in case environment variable was set after import
    global api_key
    if not api_key:
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GEMINI_API_KEY is not set in environment or .env file.")
        genai.configure(api_key=api_key)
        
    try:
        response = genai.embed_content(
            model="models/gemini-embedding-001",
            content=text,
            task_type="retrieval_document"
        )
        return response['embedding']
    except Exception as e:
        raise RuntimeError(f"Failed to generate embedding from Gemini API: {str(e)}")
