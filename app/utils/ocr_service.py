import requests
import base64
import os

class OCRService:
    """
    Handles interaction with OCR APIs (Puter AI).
    """

    @staticmethod
    def get_token():
        """Tries to read the Puter token from secrets or environment variables."""
        try:
            import streamlit as st
            if "PUTER_TOKEN" in st.secrets:
                return st.secrets["PUTER_TOKEN"]
            elif "puter" in st.secrets and "token" in st.secrets["puter"]:
                return st.secrets["puter"]["token"]
        except Exception:
            pass
        return os.environ.get("PUTER_TOKEN")

    @staticmethod
    def extract_text(image_path):
        """
        Sends image to Puter AI (GPT-4o-mini) and returns extracted text/latex.
        Returns a tuple: (success: bool, content: str)
        """
        if not os.path.exists(image_path):
            return False, "Error: File not found."

        token = OCRService.get_token()
        if not token:
            # Fallback option for simulation mode if needed
            # return OCRService._simulate_api_call(image_path)
            return False, "Puter API token is missing. Please add `PUTER_TOKEN` to your Streamlit secrets or environment variables."

        # 1. Encode image to base64
        try:
            ext = image_path.split(".")[-1].lower()
            if ext in ["jpg", "jpeg"]:
                mime_type = "image/jpeg"
            elif ext == "png":
                mime_type = "image/png"
            elif ext == "webp":
                mime_type = "image/webp"
            elif ext == "gif":
                mime_type = "image/gif"
            else:
                mime_type = "image/jpeg"
            with open(image_path, "rb") as image_file:
                image_base64 = base64.b64encode(image_file.read()).decode("utf-8")
        except Exception as e:
            return False, f"Error processing image: {str(e)}"

        # 2. Prepare Payload for Puter AI (using GPT-4o-mini with multimodal format)
        url = "https://api.puter.com/puterai/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an expert OCR engine. Extract all text and questions from the image. "
                        "Identify any mathematical formulas, variables, equations, or scientific symbols "
                        "and wrap them in standard LaTeX delimiters (e.g., use $...$ for inline math like "
                        "$x^2 + y^2 = r^2$, and $$...$$ for block equations). "
                        "Return ONLY the extracted text/questions. Do not wrap the response in markdown blocks "
                        "(like ``` or ```json), and do not include conversational text or explanations."
                    )
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "Perform OCR on this image, keeping math formatted in LaTeX."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_base64}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.3
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=30)
            if response.status_code == 200:
                response_json = response.json()
                if "choices" in response_json and len(response_json["choices"]) > 0:
                    extracted_text = response_json["choices"][0]["message"]["content"].strip()
                    # Clean up any markdown code block wraps (e.g., ```latex ... ```)
                    if extracted_text.startswith("```"):
                        lines = extracted_text.splitlines()
                        if len(lines) >= 2:
                            if lines[0].startswith("```"):
                                lines = lines[1:]
                            if lines[-1].startswith("```"):
                                lines = lines[:-1]
                            extracted_text = "\n".join(lines).strip()
                    return True, extracted_text
                return False, f"Unexpected API response format: {response_json}"
            else:
                try:
                    err_msg = response.json().get("error", {}).get("message", "Unknown error")
                except Exception:
                    err_msg = response.text
                return False, f"Puter AI OCR Error (Status {response.status_code}): {err_msg}"
        except Exception as e:
            return False, f"Connection Failure: {str(e)}"

    @staticmethod
    def _simulate_api_call(image_path):
        """Temporary mock function for testing UI flow."""
        import time
        time.sleep(1) # Simulate network delay
        return True, "Calculate the value of $\\int_{0}^{\\pi} \\sin(x) dx$ using integration by parts."