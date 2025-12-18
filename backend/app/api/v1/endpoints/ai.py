from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.ollama_tracker import ollama_tracker
from app.api.deps import get_db

router = APIRouter()


class GenerateRequest(BaseModel):
    prompt: str
    system_prompt: Optional[str] = None
    temperature: float = 0.7
    user_id: int = 1


class ChatRequest(BaseModel):
    messages: List[Dict[str, str]]
    temperature: float = 0.7
    user_id: int = 1


class AnswerQuestionRequest(BaseModel):
    question: str
    user_profile: Dict
    job_details: Dict
    user_id: int = 1
    job_id: Optional[int] = None


class CoverLetterRequest(BaseModel):
    user_profile: Dict
    job_details: Dict
    template: Optional[str] = None
    user_id: int = 1
    job_id: Optional[int] = None


@router.post("/generate")
async def generate_text(
    request: GenerateRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate text using Ollama with token tracking
    """
    try:
        response = await ollama_tracker.generate_with_tracking(
            prompt=request.prompt,
            db=db,
            user_id=request.user_id,
            operation_type="text_generation",
            system_prompt=request.system_prompt,
            temperature=request.temperature,
            endpoint="/ai/generate"
        )
        
        return {
            "success": True,
            "response": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Chat with Ollama with token tracking
    """
    try:
        response = await ollama_tracker.chat_with_tracking(
            messages=request.messages,
            db=db,
            user_id=request.user_id,
            operation_type="chat",
            temperature=request.temperature,
            endpoint="/ai/chat"
        )
        
        return {
            "success": True,
            "response": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer-question")
async def answer_job_question(
    request: AnswerQuestionRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Answer a job application question using AI with token tracking
    """
    try:
        answer = await ollama_tracker.answer_job_question_with_tracking(
            question=request.question,
            user_profile=request.user_profile,
            job_details=request.job_details,
            db=db,
            user_id=request.user_id,
            job_id=request.job_id
        )
        
        return {
            "success": True,
            "question": request.question,
            "answer": answer
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-cover-letter")
async def generate_cover_letter(
    request: CoverLetterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Generate a cover letter using AI with token tracking
    """
    try:
        cover_letter = await ollama_tracker.generate_cover_letter_with_tracking(
            user_profile=request.user_profile,
            job_details=request.job_details,
            db=db,
            user_id=request.user_id,
            job_id=request.job_id,
            template=request.template
        )
        
        return {
            "success": True,
            "cover_letter": cover_letter
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))