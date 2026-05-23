import os
import json
import PyPDF2
from google import genai
from google.genai import types
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def extract_text_from_pdf(pdf_path):
    """
    Extracts all text from a given PDF file path using PyPDF2.
    """
    text = ""
    with open(pdf_path, 'rb') as f:
        reader = PyPDF2.PdfReader(f)
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text

def process_audit(tender_pdf_path, bid_pdf_path):
    """
    Loads GEMINI_API_KEY from environment, extracts text from the provided
    Tender and Vendor PDFs, compares them using gemini-1.5-flash, and returns
    a parsed audit result dictionary matching the requested schema.
    
    Args:
        tender_pdf_path (str): File path to the Tender Document PDF.
        bid_pdf_path (str): File path to the Vendor Bid PDF.
        
    Returns:
        dict: A dictionary containing 'status', 'score', 'summary', and 'key_findings'.
    """
    try:
        # Load environment variables and retrieve the API key
        load_dotenv()
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return {
                "status": "error",
                "score": 0,
                "summary": "Missing GEMINI_API_KEY. Please set it in your .env file.",
                "key_findings": []
            }

        # Configure Google GenAI Client
        client = genai.Client(api_key=api_key)

        # Extract text from PDFs
        tender_text = extract_text_from_pdf(tender_pdf_path)
        bid_text = extract_text_from_pdf(bid_pdf_path)

        if not tender_text.strip():
            raise ValueError("Tender Document PDF is empty or could not be read.")
        if not bid_text.strip():
            raise ValueError("Vendor Bid PDF is empty or could not be read.")

        # Construct prompt exactly as instructed
        prompt = (
            "You are an impartial agricultural auditor. Compare the required specifications in the Tender Document "
            "against the offered specifications in the Vendor Bid. Return ONLY a valid JSON object with these exact keys: "
            "\"status\" (string: \"success\"), \"score\" (integer out of 100), \"summary\" (a short string explaining the score), "
            "and \"key_findings\" (a list of objects, each containing \"criterion\", \"status\" (Match/Deviation), and \"notes\").\n\n"
            f"TENDER DOCUMENT:\n{tender_text}\n\n"
            f"VENDOR BID:\n{bid_text}"
        )

        # Call Gemini model ensuring structured JSON output
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )

        # Parse and return JSON response
        result_text = response.text
        if not result_text:
            raise ValueError("Empty response received from the Gemini API.")

        print('RAW MODEL OUTPUT:', response.text)
        cleaned_text = response.text.replace('```json', '').replace('```', '').strip()
        result_dict = json.loads(cleaned_text)
        
        # Verify schema requirements
        required_keys = ["status", "score", "summary", "key_findings"]
        for key in required_keys:
            if key not in result_dict:
                raise KeyError(f"Expected key '{key}' was not found in response JSON.")
                
        return result_dict

    except Exception as e:
        return {'status': 'error', 'message': str(e)}


def audit_procurement(tender_file, vendor_file):
    """
    Audits the vendor bid against the tender document (backward compatible / temporary).
    Currently returns a placeholder JSON response.
    """
    result = {
        "status": "success",
        "score": 85,
        "summary": "This is a placeholder summary from the agent. The vendor bid meets the baseline criteria outlined in the tender document with minor deviations.",
        "key_findings": [
            {
                "criterion": "Technical Specifications",
                "status": "Match",
                "notes": "Vendor bid aligns with the required agricultural machinery specifications."
            },
            {
                "criterion": "Pricing & Commercials",
                "status": "Deviation",
                "notes": "Overall bid price is 8% above the estimated budget specified in the tender."
            },
            {
                "criterion": "Delivery Schedule",
                "status": "Match",
                "notes": "Proposed delivery timeline of 45 days is well within the 60-day limit."
            }
        ]
    }
    return result

