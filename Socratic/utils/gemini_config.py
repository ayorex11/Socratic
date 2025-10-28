import google.generativeai as genai
import os
from django.conf import settings

class GeminiConfig:
    """
    Configuration for Google Gemini API
    """
    
    _configured = False
    
    @classmethod
    def configure(cls):
        """Configure Gemini API with your key"""
        if cls._configured:
            return
            
        try:
            # Get API key from environment or Django settings
            api_key = os.getenv('GEMINI_API_KEY')
            
            if not api_key:
                raise ValueError("GEMINI_API_KEY not found in environment variables.")
            
            genai.configure(api_key=api_key)
            cls._configured = True
            print("Gemini API configured successfully!")
            
        except Exception as e:
            print(f"Error configuring Gemini: {str(e)}")
            raise

    @classmethod
    def get_model(cls, model_name="gemini-2.5-flash"):
        """Get Gemini model instance"""
        if not cls._configured:
            cls.configure()
        
        return genai.GenerativeModel(model_name)