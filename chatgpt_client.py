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
        """创建分析prompt"""
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
        """计算指数退避等待时间，加上随机抖动"""
        base_wait = min(self.backoff_base ** attempt, self.backoff_cap)
        # 添加随机抖动 (±20%)
        jitter = base_wait * 0.2 * (2 * random.random() - 1)
        return max(1.0, base_wait + jitter)
    
    def _handle_rate_limit_error(self, response) -> Optional[int]:
        """处理限速错误，返回建议等待时间"""
        try:
            # 检查响应头中的重试建议
            retry_after = response.headers.get('Retry-After')
            if retry_after:
                return int(retry_after)
            
            # 检查响应体中的错误信息
            error_data = response.json()
            if 'error' in error_data:
                error_msg = error_data['error'].get('message', '')
                if 'Rate limit' in error_msg or 'quota' in error_msg.lower():
                    # 从错误信息中提取等待时间
                    if 'Try again in' in error_msg:
                        # 例如: "Try again in 20s"
                        import re
                        match = re.search(r'Try again in (\d+)s', error_msg)
                        if match:
                            return int(match.group(1))
                        # 例如: "Try again in 1m12s" 
                        match = re.search(r'Try again in (\d+)m(\d+)s', error_msg)
                        if match:
                            return int(match.group(1)) * 60 + int(match.group(2))
            
        except Exception as e:
            print(f"解析限速错误时出现异常: {e}")
        
        return None
    
    def analyze_case(self, case_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """分析case数据，调用ChatGPT API并处理各种错误情况"""
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
                print(f"  API调用尝试 {attempt + 1}/{self.max_retries}...")
                
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=payload,
                    timeout=120  # 增加超时时间
                )
                
                # 成功响应
                if response.status_code == 200:
                    try:
                        result = response.json()
                        content = result['choices'][0]['message']['content']
                        
                        # 清理JSON内容
                        content = content.strip()
                        if content.startswith('```json'):
                            content = content[7:]
                        elif content.startswith('```'):
                            content = content[3:]
                        if content.endswith('```'):
                            content = content[:-3]
                        content = content.strip()
                        
                        # 解析JSON
                        parsed_result = json.loads(content)
                        print(f"  ✓ API调用成功")
                        return parsed_result
                        
                    except json.JSONDecodeError as e:
                        print(f"  JSON解析错误 (尝试 {attempt + 1}): {str(e)}")
                        print(f"  响应内容前200字符: {content[:200]}...")
                        
                        if attempt == self.max_retries - 1:
                            print(f"  ✗ 所有重试都失败了，JSON解析错误")
                            return None
                        
                        # JSON解析错误，短暂等待后重试
                        wait_time = 2.0
                        print(f"  等待 {wait_time:.1f} 秒后重试...")
                        time.sleep(wait_time)
                        continue
                
                # 429 限速错误
                elif response.status_code == 429:
                    suggested_wait = self._handle_rate_limit_error(response)
                    
                    if suggested_wait:
                        wait_time = min(suggested_wait + 5, self.backoff_cap)  # 加5秒缓冲
                    else:
                        wait_time = self._calculate_wait_time(attempt)
                    
                    print(f"  ⚠️ API限速 (429)，等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                
                # 5xx 服务器错误
                elif response.status_code >= 500:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  ⚠️ 服务器错误 ({response.status_code})，等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                
                # 4xx 客户端错误 (除了429)
                elif response.status_code >= 400:
                    print(f"  ✗ 客户端错误 ({response.status_code}): {response.text[:200]}")
                    return None
                
                # 其他错误
                else:
                    print(f"  ⚠️ 未知状态码 ({response.status_code})，尝试重试...")
                    if attempt < self.max_retries - 1:
                        wait_time = self._calculate_wait_time(attempt)
                        time.sleep(wait_time)
                        continue
                    else:
                        print(f"  ✗ API请求失败，状态码: {response.status_code}")
                        print(f"  错误信息: {response.text[:200]}")
                        return None
                        
            except requests.exceptions.Timeout:
                print(f"  ⚠️ 请求超时 (尝试 {attempt + 1})")
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ✗ 请求超时，所有重试失败")
                    return None
                    
            except requests.exceptions.ConnectionError:
                print(f"  ⚠️ 连接错误 (尝试 {attempt + 1})")
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ✗ 连接错误，所有重试失败")
                    return None
                    
            except requests.exceptions.RequestException as e:
                print(f"  ⚠️ 请求异常 (尝试 {attempt + 1}): {str(e)}")
                if attempt < self.max_retries - 1:
                    wait_time = self._calculate_wait_time(attempt)
                    print(f"  等待 {wait_time:.1f} 秒后重试...")
                    time.sleep(wait_time)
                    continue
                else:
                    print(f"  ✗ 请求异常，所有重试失败")
                    return None
        
        print(f"  ✗ 达到最大重试次数 ({self.max_retries})，API调用失败")
        return None