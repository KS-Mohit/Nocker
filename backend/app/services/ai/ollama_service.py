from typing import Dict, List, Optional
from loguru import logger
import httpx
import google.generativeai as genai
import json
from app.core.config import settings


class OllamaService:
    """Hybrid Service: Uses Ollama for Text/Chat and Google Gemini for Vision/OCR"""
    
    def __init__(self):
        # 1. Setup Local Ollama (Text)
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)

        # 2. Setup Google Gemini (Vision)
        if settings.GOOGLE_API_KEY:
            try:
                genai.configure(api_key=settings.GOOGLE_API_KEY)
                # Use 'gemini-2.5-flash' as the current stable version for OCR/Vision
                self.vision_model = genai.GenerativeModel('gemini-2.5-flash')
                logger.info("✅ Google Gemini Vision initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                self.vision_model = None
        else:
            logger.warning("⚠️ GOOGLE_API_KEY not found. Vision features will fail.")
            self.vision_model = None
    
    async def parse_job_screenshot(self, image_bytes: bytes) -> Dict:
        """
        Visual Parsing: Sends screenshot to Gemini to extract structured JSON data.
        """
        if not self.vision_model:
            logger.error("Google API Key missing. Cannot parse screenshots.")
            return {}

        try:
            logger.info("👀 Sending screenshot to Gemini for visual parsing...")

            # 1. Prepare Image Payload
            image_part = {
                "mime_type": "image/png",
                "data": image_bytes
            }

            # 2. Strict Prompt for JSON Extraction
            prompt = """
            You are a data extraction agent. Analyze this job posting screenshot.
            Extract the following fields into a valid JSON object:
            {
                "title": "Exact Job Title",
                "company": "Company Name",
                "location": "Location (City, State or Remote)",
                "workplace_type": "Remote, On-site, or Hybrid",
                "job_type": "Full-time, Contract, etc",
                "description": "Full text of the job description",
                "is_easy_apply": true/false (if you see an 'Easy Apply' button)
            }
            Important: Return ONLY the raw JSON. Do not use Markdown formatting like ```json.
            """

            # 3. Call Gemini API (Runs in cloud)
            # generate_content is synchronous, so we wrap it if needed, but usually it's fast enough.
            response = self.vision_model.generate_content([prompt, image_part])
            
            # 4. Parse Response
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_json)
            
            logger.info(f"✅ Visual Parse Success: {data.get('title')} at {data.get('company')}")
            return data

        except Exception as e:
            logger.error(f"❌ Visual Parsing Failed: {e}")
            return {}

    async def analyze_form_screenshot(self, image_bytes: bytes, user_profile: Dict) -> List[Dict]:
        """
        Vision AI: Analyzes a form screenshot and maps user data to fields.
        Returns a list of actions to take.
        """
        if not self.vision_model:
            logger.error("Google Vision API not initialized")
            return []

        try:
            logger.info("🧠 Analyzing form fields with Vision AI...")

            # 1. Simplify User Profile for the AI (Save tokens, keep it relevant)
            # We convert the profile to a clean string format
            profile_context = json.dumps({
                "full_name": user_profile.get("full_name"),
                "email": user_profile.get("email"),
                "phone": user_profile.get("phone"),
                "current_job": user_profile.get("work_experience", [{}])[0].get("title", "N/A"),
                "current_company": user_profile.get("work_experience", [{}])[0].get("company", "N/A"),
                "linkedin": user_profile.get("linkedin_url"),
                "portfolio": user_profile.get("portfolio_url"),
                "location": user_profile.get("location"),
                "skills": user_profile.get("skills", [])[:10], # Top 10 skills
                "experience_years": 5 # Example: You might want to calculate this dynamically
            }, indent=2)

            # 2. The Vision Prompt
            prompt = f"""
            You are an autonomous form-filling agent. 
            Look at this screenshot of a job application form.
            
            USER PROFILE:
            {profile_context}

            INSTRUCTIONS:
            1. Identify every visible input field (Text, Radio, Checkbox, Dropdown).
            2. Match the field to the User Profile data provided above.
            3. If the question is a custom question (e.g., "Why do you want this job?"), generate a short, professional answer.
            4. If there is a "Next", "Continue", or "Review" button, include it as the final action.
            5. IGNORE the "Easy Apply" button or "X" close buttons. Focus on the form content.

            OUTPUT FORMAT (JSON ONLY):
            Return a JSON List of actions. format:
            [
                {{ "action": "fill", "label_text": "First name", "value": "John" }},
                {{ "action": "click", "label_text": "Yes" }}, (For radio/checkbox)
                {{ "action": "select", "label_text": "Country", "value": "United States" }},
                {{ "action": "click_button", "text": "Next" }}
            ]
            """

            image_part = {"mime_type": "image/png", "data": image_bytes}
            
            # 3. Call Gemini
            response = self.vision_model.generate_content([prompt, image_part])
            
            # 4. Clean and Parse
            clean_json = response.text.replace("```json", "").replace("```", "").strip()
            actions = json.loads(clean_json)
            
            logger.info(f"⚡ AI identified {len(actions)} actions to perform.")
            return actions

        except Exception as e:
            logger.error(f"❌ Form Analysis Failed: {e}")
            return []

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate text using Ollama
        """
        try:
            logger.info(f"Generating response with {self.model}...")
            
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            if system_prompt:
                payload["system"] = system_prompt
            
            response = await self.client.post(
                f"{self.base_url}/api/generate",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            generated_text = result.get("response", "").strip()
            
            logger.info(f"Generated {len(generated_text)} characters")
            return generated_text
            
        except Exception as e:
            logger.error(f"Ollama generation error: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Chat with Ollama using conversation history
        """
        try:
            logger.info(f"Chat with {len(messages)} messages...")
            
            payload = {
                "model": self.model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": temperature,
                    "num_predict": max_tokens
                }
            }
            
            response = await self.client.post(
                f"{self.base_url}/api/chat",
                json=payload
            )
            response.raise_for_status()
            
            result = response.json()
            message = result.get("message", {})
            content = message.get("content", "").strip()
            
            logger.info(f"Response: {content[:100]}...")
            return content
            
        except Exception as e:
            logger.error(f"Ollama chat error: {e}")
            raise

    async def answer_job_question(
        self,
        question: str,
        user_profile: Dict,
        job_details: Dict
    ) -> str:
        """
        Answer a job application question using user profile
        """
        try:
            context = self._build_user_context(user_profile)
            
            system_prompt = """You are a professional career advisor helping someone answer job application questions.
            
Guidelines:
- Keep answers concise (2-3 sentences)
- Be professional and confident
- Use specific examples from the user's experience
- Tailor responses to the job requirements
- Be honest but positive"""
            
            user_prompt = f"""Job Details:
- Company: {job_details.get('company', 'Unknown')}
- Position: {job_details.get('title', 'Unknown')}
- Description: {job_details.get('description', 'N/A')[:500]}

User Profile:
{context}

Question: {question}

Provide a professional answer based on the user's profile:"""
            
            answer = await self.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.7,
                max_tokens=300
            )
            
            return answer
            
        except Exception as e:
            logger.error(f"Error answering question: {e}")
            raise

    async def generate_cover_letter(
        self,
        user_profile: Dict,
        job_details: Dict,
        template: Optional[str] = None
    ) -> str:
        """
        Generate a tailored cover letter
        """
        try:
            context = self._build_user_context(user_profile)
            
            system_prompt = """You are an expert at writing professional cover letters.

Guidelines:
- Keep it under 300 words
- Show enthusiasm for the role
- Highlight relevant experience
- Explain why you're a good fit
- Be professional but personable
- Include a strong opening and closing"""
            
            user_prompt = f"""Write a cover letter for this job:

Company: {job_details.get('company')}
Position: {job_details.get('title')}
Location: {job_details.get('location')}
Description: {job_details.get('description', '')[:800]}

Applicant Profile:
{context}

{"Use this structure: " + template if template else ""}

Write a compelling cover letter:"""
            
            cover_letter = await self.generate(
                prompt=user_prompt,
                system_prompt=system_prompt,
                temperature=0.8,
                max_tokens=800
            )
            
            return cover_letter
            
        except Exception as e:
            logger.error(f"Error generating cover letter: {e}")
            raise

    def _build_user_context(self, user_profile: Dict) -> str:
        """Build context string from user profile"""
        context_parts = []
        
        if user_profile.get('full_name'):
            context_parts.append(f"Name: {user_profile['full_name']}")
        
        if user_profile.get('summary'):
            context_parts.append(f"Summary: {user_profile['summary']}")
        
        if user_profile.get('work_experience'):
            context_parts.append("Work Experience:")
            for exp in user_profile['work_experience'][:3]:
                context_parts.append(f"- {exp.get('title')} at {exp.get('company')}: {exp.get('description', '')[:200]}")
        
        if user_profile.get('skills'):
            skills_str = ", ".join(user_profile['skills'][:10])
            context_parts.append(f"Skills: {skills_str}")
        
        if user_profile.get('education'):
            context_parts.append("Education:")
            for edu in user_profile['education']:
                context_parts.append(f"- {edu.get('degree')} from {edu.get('school')}")
        
        return "\n".join(context_parts)

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()