from typing import Dict, Optional, List
import re
import json
from loguru import logger
import PyPDF2
from io import BytesIO

class ResumeParser:
    """Parse resume PDF and extract structured data"""
    
    def __init__(self):
        pass
    
    def extract_text_from_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from PDF bytes"""
        try:
            pdf_file = BytesIO(pdf_bytes)
            pdf_reader = PyPDF2.PdfReader(pdf_file)
            
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text()
            
            logger.info(f"Extracted {len(text)} characters from PDF")
            return text
            
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            raise
    
    def extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        return emails[0] if emails else None
    
    def extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        # Common phone patterns
        patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # +1-555-555-5555
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',  # (555) 555-5555
        ]
        
        for pattern in patterns:
            phones = re.findall(pattern, text)
            if phones:
                return phones[0]
        return None
    
    def extract_urls(self, text: str) -> Dict[str, Optional[str]]:
        """Extract LinkedIn, GitHub, Portfolio URLs"""
        urls = {
            "linkedin_url": None,
            "github_url": None,
            "portfolio_url": None
        }
        
        # LinkedIn
        linkedin_pattern = r'linkedin\.com/in/[\w-]+'
        linkedin_matches = re.findall(linkedin_pattern, text, re.IGNORECASE)
        if linkedin_matches:
            urls["linkedin_url"] = f"https://{linkedin_matches[0]}"
        
        # GitHub
        github_pattern = r'github\.com/[\w-]+'
        github_matches = re.findall(github_pattern, text, re.IGNORECASE)
        if github_matches:
            urls["github_url"] = f"https://{github_matches[0]}"
        
        # Portfolio (generic URL that's not LinkedIn/GitHub)
        url_pattern = r'https?://(?:www\.)?[\w.-]+\.[\w]{2,}'
        all_urls = re.findall(url_pattern, text)
        for url in all_urls:
            if 'linkedin' not in url.lower() and 'github' not in url.lower():
                urls["portfolio_url"] = url
                break
        
        return urls
    
    def extract_name(self, text: str) -> Optional[str]:
        """
        Extract name from resume (usually first line or after common headers)
        This is a simple heuristic - may need improvement
        """
        lines = text.strip().split('\n')
        
        # Skip empty lines and common headers
        skip_keywords = ['resume', 'cv', 'curriculum vitae', 'profile', 'about']
        
        for line in lines[:10]:  # Check first 10 lines
            line = line.strip()
            if not line:
                continue
            
            # Skip if it's a common header
            if any(keyword in line.lower() for keyword in skip_keywords):
                continue
            
            # If line looks like a name (2-3 words, capitalized)
            words = line.split()
            if 2 <= len(words) <= 3 and all(word[0].isupper() for word in words if word):
                return line
        
        return None
    
    def extract_skills_section(self, text: str) -> list:
        """Extract skills from common skills section"""
        skills = []
        
        # Find skills section
        skills_pattern = r'(?:SKILLS|TECHNICAL SKILLS|TECHNOLOGIES)[:\n](.*?)(?=\n[A-Z]{2,}|\Z)'
        skills_match = re.search(skills_pattern, text, re.IGNORECASE | re.DOTALL)
        
        if skills_match:
            skills_text = skills_match.group(1)
            
            # Common skill keywords to look for
            common_skills = [
                'Python', 'JavaScript', 'Java', 'C++', 'C#', 'Go', 'Rust', 'Ruby', 'PHP',
                'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'FastAPI',
                'PostgreSQL', 'MySQL', 'MongoDB', 'Redis', 'SQL',
                'Docker', 'Kubernetes', 'AWS', 'Azure', 'GCP',
                'Git', 'CI/CD', 'Jenkins', 'GitHub Actions',
                'Machine Learning', 'Deep Learning', 'TensorFlow', 'PyTorch',
                'REST API', 'GraphQL', 'Microservices',
                'Linux', 'Bash', 'Shell Scripting'
            ]
            
            for skill in common_skills:
                if re.search(rf'\b{skill}\b', skills_text, re.IGNORECASE):
                    skills.append(skill)
        
        return skills if skills else []

async def parse_resume_with_ai(resume_text: str, ollama_service) -> Dict:
    """
    Use AI to extract structured data from resume text.
    Includes robust JSON extraction to handle Llama's conversational output.
    """
    system_prompt = """You are an expert resume parser. 
    Your task is to extract information from the resume text provided and return it in strict JSON format.
    
    Rules:
    1. Return ONLY the JSON object. 
    2. Do not add introductory text or markdown formatting.
    3. Use "null" for missing fields.
    
    Schema:
    {
      "full_name": "string",
      "email": "string",
      "phone": "string",
      "location": "string",
      "summary": "string",
      "work_experience": [
        {
          "title": "string",
          "company": "string",
          "location": "string",
          "start_date": "string",
          "end_date": "string",
          "description": "string",
          "technologies": ["string"]
        }
      ],
      "education": [
        {
          "degree": "string",
          "school": "string",
          "graduation_year": "string"
        }
      ],
      "skills": ["string"],
      "certifications": [
        {
          "name": "string",
          "issuer": "string"
        }
      ],
      "projects": [
        {
          "name": "string",
          "description": "string",
          "technologies": ["string"],
          "url": "string"
        }
      ]
    }
    """
    
    user_prompt = f"""Resume Text:
    {resume_text}
    
    Extract the data into JSON now:"""

    try:
        response = await ollama_service.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.1,
            max_tokens=3000
        )
        
        # Robust JSON Extraction Logic
        cleaned_response = response.strip()
        
        # Find the first '{' and the last '}'
        start_idx = cleaned_response.find('{')
        end_idx = cleaned_response.rfind('}')
        
        if start_idx != -1 and end_idx != -1:
            json_str = cleaned_response[start_idx : end_idx + 1]
            parsed_data = json.loads(json_str)
            logger.info("Successfully parsed AI JSON response")
            return parsed_data
        else:
            logger.error(f"Could not find JSON braces in response. Raw output:\n{cleaned_response[:500]}...")
            raise ValueError("AI did not return valid JSON")

    except json.JSONDecodeError as e:
        logger.error(f"JSON Decode Error: {e}")
        logger.error(f"Raw content attempting to parse:\n{response}")
        raise
    except Exception as e:
        logger.error(f"AI parsing error: {e}")
        raise