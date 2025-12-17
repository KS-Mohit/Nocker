from typing import Dict, List, Optional
from loguru import logger
import httpx
from app.core.config import settings


class OllamaService:
    """Service for interacting with Ollama LLM"""
    
    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.client = httpx.AsyncClient(timeout=120.0)
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate text using Ollama
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Randomness (0-1, lower = more focused)
            max_tokens: Maximum response length
            
        Returns:
            Generated text
        """
        try:
            logger.info(f"Generating response with {self.model}...")
            
            # Prepare request
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
            
            # Call Ollama API
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
        
        Args:
            messages: List of {"role": "user/assistant/system", "content": "..."}
            temperature: Randomness
            max_tokens: Max response length
            
        Returns:
            Assistant's response
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
        
        Args:
            question: Application question
            user_profile: User's resume/experience data
            job_details: Job title, company, description
            
        Returns:
            AI-generated answer
        """
        try:
            # Build context from user profile
            context = self._build_user_context(user_profile)
            
            # Build prompt
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
        
        Args:
            user_profile: User's experience data
            job_details: Job information
            template: Optional template to follow
            
        Returns:
            Generated cover letter
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
            for exp in user_profile['work_experience'][:3]:  # Top 3
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