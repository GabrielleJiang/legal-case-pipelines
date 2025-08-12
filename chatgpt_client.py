"""
ChatGPT API Client
"""

import json
import requests
import time
from typing import Dict, Any, Optional


class ChatGPTClient:
    """ChatGPT API Client"""
    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def create_prompt(self, case_data: Dict[str, Any]) -> str:
        """Create analysis prompt"""
        prompt = f"""
**Prompt for Background Sections – Used to Identify Defendant Companies**

INPUT: A JSON object with the following fields:
```json
{json.dumps(case_data, indent=2, ensure_ascii=False)}
```

TASK: For EACH case, analyze only the provided text and return ONE JSON object with EXACTLY these fields:

1. "Case ID": copy exactly from input.
2. "Filename": copy exactly from input.
3. "Defendant Type": strictly choose "Individual Only" OR "Individual and Company".
4. "ExtractedComapny_Individual":
   - Only fill this field if Defendant Type is "Individual Only".
   - List up to 3 company names that the individual defendant (any person listed the "def_key" section in the input file) **founded, co-founded, created, established, organized, formed, set up, incorporated, owned, controlled, ran, directed, managed, was a principal of, or held an officer/director role in** during the illegal activity period.
   - A valid company name must meet ONE of these:
     * Contains one of these keywords (case-insensitive): CO, LTD, LLC, CORP, LIMITED, PARTNERSHIP, CORPORATION, INC, INCORPORATED, COMPANY, LP.
     * OR is written in ALL CAPS or has a parenthetical abbreviation (e.g., "Medical Safety Solutions (MSS)" or "MSS") **and** is explicitly linked to the defendant via the above relationship verbs.
   - Separate multiple company names with ";". If no qualifying company is explicitly linked, return an empty string.
5. "ExtractedComapny_Both":
   - Only fill this field if Defendant Type is "Individual and Company".
   - List up to 3 company names that are explicitly named as **defendant companies** in the case.
   - Apply the same name rules as above.
   - Separate multiple names with ";" or leave empty string if unclear.
6. "ExtractEvidence":
   - For each extracted company, copy the exact sentence or sentence fragment from the text that links the defendant and the company.
   - Format each as: `Company => sentence`.
   - Separate multiple entries with ";". If no company is extracted, return an empty string.

CONSTRAINTS:
- Use only information explicitly stated or strongly implied by the text. Do NOT invent names or links.
- Do not add commentary, explanations, or extra fields.
- Ensure the JSON output is syntactically valid.

Return ONLY the JSON result with no additional text or explanations.
"""
        return prompt
    
    def analyze_case(self, case_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze case data with single API call (no retries)"""
        prompt = self.create_prompt(case_data)
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a professional legal document analysis assistant. Please strictly follow the requirements to analyze cases and return accurate JSON format results."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens": 600,
            "temperature": 0,
            "response_format": {"type": "json_object"}
        }
        
        try:
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                
                try:
                    content = content.strip()
                    if content.startswith('```json'):
                        content = content[7:]
                    if content.endswith('```'):
                        content = content[:-3]
                    content = content.strip()
                    
                    parsed_result = json.loads(content)
                    return parsed_result
                    
                except json.JSONDecodeError as e:
                    print(f"JSON parsing error: {str(e)}")
                    print(f"Content preview: {content[:200]}...")
                    return None
            
            else:
                print(f"API request failed, status code: {response.status_code}")
                print(f"Error message: {response.text}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Request exception: {str(e)}")
            return None
        
        return None