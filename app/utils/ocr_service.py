import requests
import base64
import json
import os

class OCRService:
    """
    Handles interaction with OCR APIs (Mathpix).
    """
    # Dynamically load credentials from env vars or streamlit secrets
    APP_ID = os.environ.get("MATHPIX_APP_ID", "YOUR_MATHPIX_APP_ID")
    APP_KEY = os.environ.get("MATHPIX_APP_KEY", "YOUR_MATHPIX_APP_KEY")
    
    # Try reading from Streamlit secrets if running inside Streamlit
    try:
        import streamlit as st
        if "MATHPIX_APP_ID" in st.secrets:
            APP_ID = st.secrets["MATHPIX_APP_ID"]
        if "MATHPIX_APP_KEY" in st.secrets:
            APP_KEY = st.secrets["MATHPIX_APP_KEY"]
    except Exception:
        pass

    API_URL = "https://api.mathpix.com/v3/text"

    @staticmethod
    def extract_text(image_path):
        """
        Sends image to API and returns extracted text/latex.
        Returns a tuple: (success: bool, content: str)
        """
        if not os.path.exists(image_path):
            return False, "Error: File not found."

        # 1. Encode image to base64
        try:
            with open(image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            return False, f"Error processing image: {str(e)}"

        # 2. Prepare Payload (Configuration for Mathpix)
        headers = {
            "app_id": OCRService.APP_ID,
            "app_key": OCRService.APP_KEY,
            "Content-type": "application/json"
        }
        
        data = {
            "src": f"data:image/jpeg;base64,{image_base64}",
            "formats": ["text", "latex_simplified"],
            "data_options": {
                "include_asciimath": False
            }
        }

        # 3. Send Request (Simulated for Phase 3 dev without keys)
        # return OCRService._simulate_api_call(image_path) # UNCOMMENT THIS TO TEST WITHOUT KEY
        
        # REAL CALL (Will fail without valid keys)
        try:
            response = requests.post(OCRService.API_URL, json=data, headers=headers, timeout=10)
            response_json = response.json()
            
            if "text" in response_json:
                return True, response_json["text"]
            elif "error" in response_json:
                return False, f"API Error: {response_json['error']}"
            else:
                return False, "Unknown API response."
        except Exception as e:
            return False, f"Connection Error: {str(e)}"

    @staticmethod
    def _simulate_api_call(image_path):
        """Temporary mock function for testing UI flow."""
        import time
        time.sleep(1) # Simulate network delay
        return True, "Calculate the value of $\\int_{0}^{\\pi} \\sin(x) dx$ using integration by parts."