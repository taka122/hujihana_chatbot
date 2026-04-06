import os
import json
from app.services.gemini_client import GeminiClient, GeminiApiError
from app.config import get_settings

def diagnostic():
    settings = get_settings()
    print(f"GEMINI_BASE_URL: {settings.gemini_base_url}")
    print(f"GEMINI_API_KEY (last 4): ...{settings.gemini_api_key[-4:] if settings.gemini_api_key else 'None'}")
    
    client = GeminiClient(api_key=settings.gemini_api_key or "", base_url=settings.gemini_base_url)
    
    # Try a simple GET request through _post (which GeminiClient uses)
    try:
        # models/gemini-pro is a valid path for GET
        res = client._post("models/gemini-pro", payload={}, method="GET")
        print("Success calling models/gemini-pro")
        # print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Error calling models/gemini-pro: {e}")

if __name__ == "__main__":
    diagnostic()
