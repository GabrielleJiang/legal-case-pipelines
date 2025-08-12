"""
ChatGPT API with improved rate limiting and retry logic
"""

import json
import requests
import time
import random
from typing import Dict, Any, Optional


class ChatGPTClient:
    """ChatGPT API with enhanced error handling and rate limiting"""
    def __init__(self, api_key: str, model: str = "gpt-4o", config=None):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://api.openai.com/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        # Load config parameters for retry logic
        if config:
            self.max_retries = config.MAX_RETRIES
            self.backoff_base = config.BACKOFF_BASE
            self.backoff_cap = config.BACKOFF_CAP
            self.request_delay = config.REQUEST_DELAY
        else:
            # Default values
            self.max_retries = 6
            self.backoff_base = 1.8
            self.backoff_cap = 45
            self.request_delay = 2.0

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
    
    def _calculate_wait_time(self, attempt: int) -> float:
        """Calculate exponential backoff wait time with random jitter"""
        base_wait = min(self.backoff_base ** attempt, self.backoff_cap)
        # Add random jitter (±20%)
        jitter = base_wait * 0.2 * (2 * random.random() - 1)
        return max(1.0, base_wait + jitter)
    
    def _handle_rate_limit_error(self, response) -> Optional[int]:
        """Handle rate limit errors and return suggested wait time"""
        try:
            # Check for retry suggestion in response headers
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                return int(retry_after)
            
            # Check for error message in response body
            error_data = response.json()
            if 'error' in error_data:
                error_msg = error_data['error'].get('message', '')
                if 'Rate limit' in error_msg or 'quota' in error_msg.lower():
                    # Extract wait time from error message
                    if 'Try again in' in error_msg:
                        # Example: "Try again in 20s"
                        import re
                        match = re.search(r'Try again in (\d+)s', error_msg)
                        if match:
                            return int(match.group(1))
                        # Example: "Try again in 1m12s" 
                        match = re.search(r'Try again in (\d+)m(\d+)s', error_msg)
                        if match:
                            return int(match.group(1)) * 60 + int(match.group(2))
            
        except Exception as e:
            print(f"Exception occurred while parsing rate limit error: {e}")
        
        return None
    
    def analyze_case(self, case_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze case data, call ChatGPT API, and handle various errors"""
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
            "max_tokens": 4000,
            "temperature": 0.1
        }
        
        for attempt in range(self.max_retries):
            try:
                print(f"  API call attempt {attempt + 1}/{self.max_retries}...")
                
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120  # Increase timeout duration
                )
                
                # Successful response
                if response.status_code == 200:
                    try:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # Clean JSON content
                        content = content.strip()
                        if content.startswith('```json'):
                            content = content[7:]
                        elif content.startswith('```'):
                            content = content[3:]
                        if content.endswith('```'):
                            content = content[:-3]
                        content = content.strip()
                        
                        # Parse JSON
                        parsed_result = json.loads(content)
                        print(f"  ✓ API call successful")
                        return parsed_result
                        
                    except json.JSONDecodeError as e:
                        print(f"  JSON parsing error (attempt {attempt + 1}): {str(e)}")
                        print(f"  Response content first 200 characters: {content[:200]}...")
                        
                        if attempt == self.max_retries - 1:
                            print(f"  ✗ All retries failed, JSON parsing error")
                            return None
                        
                        # JSON parsing error, wait briefly and retry
                        wait_time = 2.0
                        print(f"  Waiting {wait_time:.1f} seconds before retrying...")
                        time.sleep(wait_time)
                        continue
                
                # 429 Rate limit error
                elif response.status_code == 429:
                    suggested_wait = self._handle_rate_limit_error(response)
                    
                    if suggested_wait:
                        wait_time = min(suggested_wait + 5, self.backoff_cap)  # Add 5 seconds buffer
                    else:
                        wait_time = self._calculate_wait_time(attempt)
                    
                    print(f"  ⚠️ API rate limit (429), waiting {wait_time:.1f} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                
                # 5xx Server error
                elif response.status_code >= 500:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  ⚠️ Server error ({response.status_code}), waiting {wait_time:.1f} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                
                # 4xx Client error (except 429)
                elif response.status_code >= 400:
                    print(f"  ✗ Client error ({response.status_code}): {response.text[:200]}")
                    return None
                
                # Other errors
                else:
                    print(f"  ⚠️ Unknown status code ({response.status_code}), attempting retry...")
                    if attempt < self.max_retries - 1:
                        wait_time = self._calculate_wait_time(attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ✗ API request failed, status code: {response.status_code}")
                        print(f"  Error message: {response.text[:200]}")
                        return None
                        
            except requests.exceptions.Timeout:
                print(f"  ⚠️ Request timeout (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  Waiting {wait_time:.1f} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ✗ Request timeout, all retries failed")
                    return None
                    
            except requests.exceptions.ConnectionError:
                print(f"  ⚠️ Connection error (attempt {attempt + 1})")
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  Waiting {wait_time:.1f} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ✗ Connection error, all retries failed")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️ Request exception (attempt {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  Waiting {wait_time:.1f} seconds before retrying...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ✗ Request exception, all retries failed")
                    return None
        
        print(f"  ✗ Maximum retry attempts reached ({self.max_retries}), API call failed")
        return None