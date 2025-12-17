from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional

from app.services.ai.ollama_service import OllamaService

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float = 0.7


class AnswerQuestionRequest(BaseModel):
    question: str
    user_profile: Dict
    job_details: Dict


class CoverLetterRequest(BaseModel):
    user_profile: Dict
    job_details: Dict
    template: Optional[str] = None


@router.post("/generate")
async def generate_text(request: GenerateRequest):
    """
    Generate text using Ollama
    """
    ollama = OllamaService()
    
    try:
        response = await ollama.generate(
            prompt=request.prompt,
            system_prompt=request.system_prompt,
            temperature=request.temperature
        )
        
        return {
            "success": True,
            "response": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await ollama.close()


@router.post("/chat")
async def chat(request: ChatRequest):
    """
    Chat with Ollama
    """
    ollama = OllamaService()
    
    try:
        response = await ollama.chat(
            messages=request.messages,
            temperature=request.temperature
        )
        
        return {
            "success": True,
            "response": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await ollama.close()


@router.post("/answer-question")
async def answer_job_question(request: AnswerQuestionRequest):
    """
    Answer a job application question using AI
    """
    ollama = OllamaService()
    
    try:
        answer = await ollama.answer_job_question(
            question=request.question,
            user_profile=request.user_profile,
            job_details=request.job_details
        )
        
        return {
            "success": True,
            "question": request.question,
            "answer": answer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await ollama.close()


@router.post("/generate-cover-letter")
async def generate_cover_letter(request: CoverLetterRequest):
    """
    Generate a cover letter using AI
    """
    ollama = OllamaService()
    
    try:
        cover_letter = await ollama.generate_cover_letter(
            user_profile=request.user_profile,
            job_details=request.job_details,
            template=request.template
        )
        
        return {
            "success": True,
            "cover_letter": cover_letter
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await ollama.close()