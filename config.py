import os
from dotenv import load_dotenv
import json

load_dotenv()


class Config:
    def __init__(self):

        self.API_KEY = os.getenv("OPENAI_API_KEY")
        self.MODEL   = os.getenv("OPENAI_MODEL", "gpt-4o")
        

        self.API_BASE_URL = "https://api.openai.com/v1"
        self.MODEL = "gpt-4o"
        self.MAX_TOKENS = 1000
        self.TEMPERATURE = 0.1
        

        self.PDF_DIRECTORY = "./pdfs"
        self.OUTPUT_FILE = "./analysis_results.json"
        
        self.REQUEST_TIMEOUT = 60
        self.MAX_RETRIES = 3
        
        os.makedirs(self.PDF_DIRECTORY, exist_ok=True)
    
    def validate(self):
        """process to validate configuration"""
        if not self.API_KEY:
            raise ValueError("set your OpenAI API key in the file")
        
        if not os.path.exists(self.PDF_DIRECTORY):
            raise ValueError(f"PDF are not existing: {self.PDF_DIRECTORY}")
        
        return True