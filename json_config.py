"""
Configuration file for JSON processing - Contains API keys and other settings
"""

import os
from dotenv import load_dotenv

load_dotenv()


class JsonConfig:
    """Configuration class for JSON processing"""
    
    def __init__(self):
        self.API_KEY = os.getenv("OPENAI_API_KEY")
        self.MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
        
        self.API_BASE_URL = "https://api.openai.com/v1"
        self.MAX_TOKENS = 4000
        self.TEMPERATURE = 0.1
        
        self.JSON_DIRECTORY = os.getenv("JSON_DIRECTORY", "./json_files")
        self.OUTPUT_FILE = os.getenv("OUTPUT_FILE", "./analysis_results_json.json")
        self.FAILURE_LOG_FILE = os.getenv("FAILURE_LOG_FILE", "./failure_log.json")
        
        self.MAX_ITEMS_PER_FILE = int(os.getenv("MAX_ITEMS_PER_FILE", "50"))
        self.REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "60"))
        self.REQUEST_DELAY = float(os.getenv("REQUEST_DELAY", "1.0"))
        
        os.makedirs(self.JSON_DIRECTORY, exist_ok=True)
    
    def validate(self):
        """Validate configuration"""
        if not self.API_KEY or self.API_KEY == "your_api_key_here":
            raise ValueError("Please set your OpenAI API key in the .env file")
        
        if not os.path.exists(self.JSON_DIRECTORY):
            raise ValueError(f"JSON directory does not exist: {self.JSON_DIRECTORY}")
        
        return True