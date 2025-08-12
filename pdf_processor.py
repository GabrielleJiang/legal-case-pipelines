import re
from typing import List, Optional
import PyPDF2
import fitz 

class PDFProcessor:
    
    def __init__(self):
        self.defendant_keywords = [
            "defendant", "defendants", "accused", "respondent", 
            "respondents", "charged", "indicted"
        ]
        
        self.company_keywords = [
            "CO", "LTD", "LLC", "CORP", "LIMITED", "PARTNERSHIP", 
            "CORPORATION", "INC", "INCORPORATED", "COMPANY", "LP"
        ]
    
    def extract_text(self, pdf_path: str) -> str:
        text = ""
        

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            
            if text.strip():
                return text
        except Exception as e:
            print(f"fail: {str(e)}")
        

        try:
            pdf_document = fitz.open(pdf_path)
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                text += page.get_text() + "\n"
            pdf_document.close()
            
            return text
        except Exception as e:
            print(f"fail: {str(e)}")
            return ""
    
    def extract_defendant_names(self, text: str) -> List[str]:
        defendants = []
        text_lower = text.lower()
        
        defendant_patterns = [
            r"defendant[s]?\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+defendant",
            r"charges?\s+against\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+is\s+charged",
            r"([A-Z][a-z]+\s+[A-Z][a-z]+)[,\s]+was\s+indicted"
        ]
        
        for pattern in defendant_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if isinstance(match, tuple):
                    name = match[0]
                else:
                    name = match
                
                name = name.strip()
                if (len(name.split()) >= 2 and 
                    name not in defendants and
                    not any(keyword.lower() in name.lower() for keyword in self.company_keywords)):
                    defendants.append(name)
        

        if not defendants:
            name_patterns = re.findall(r'\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b', text)
            for name in name_patterns[:5]:
                if (name not in defendants and
                    not any(keyword.lower() in name.lower() for keyword in self.company_keywords)):
                    defendants.append(name)
        
        return defendants[:5]
    
    def split_into_paragraphs(self, text: str) -> List[str]:

        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\n\n', '||PARA||')
        text = text.replace('\n', ' ')
        

        paragraphs = text.split('||PARA||')
        
        cleaned_paragraphs = []
        for para in paragraphs:
            para = para.strip()
            if len(para) > 50:
                cleaned_paragraphs.append(para)
        
        if len(cleaned_paragraphs) < 3:
            sentences = re.split(r'(?<=[.!?])\s+', text)
            paragraphs = []
            current_para = ""
            
            for sentence in sentences:
                if len(current_para) + len(sentence) > 500:
                    if current_para:
                        paragraphs.append(current_para.strip())
                    current_para = sentence
                else:
                    current_para += " " + sentence if current_para else sentence
            
            if current_para:
                paragraphs.append(current_para.strip())
            
            cleaned_paragraphs = [p for p in paragraphs if len(p) > 50]
        
        return cleaned_paragraphs[:10]
    
    def extract_synopsis(self, text: str) -> Optional[str]:
        synopsis_keywords = [
            "summary", "synopsis", "abstract", "overview", 
            "background", "case summary", "executive summary"
        ]
        
        text_lower = text.lower()
        
        for keyword in synopsis_keywords:
            pattern = rf"{keyword}[:\s]*([^.]*(?:\.[^.]*?){{1,3}}\.)"
            match = re.search(pattern, text_lower, re.IGNORECASE | re.DOTALL)
            if match:
                synopsis = match.group(1).strip()
                if len(synopsis) > 100:
                    return synopsis[:500]
        
        sentences = re.split(r'(?<=[.!?])\s+', text)
        if len(sentences) >= 3:
            synopsis = '. '.join(sentences[:3]) + '.'
            return synopsis if len(synopsis) > 100 else None
        
        return None