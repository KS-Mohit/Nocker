"""
Enhanced Ollama Service with Token Tracking
Wraps existing OllamaService and adds automatic token tracking
"""
import time
from typing import Dict, List, Optional
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.ai.ollama_service import OllamaService
from app.services.tracker.token_tracker import TokenTracker


class OllamaServiceWithTracking(OllamaService):
    """
    Enhanced Ollama service with automatic token tracking.
    Inherits all methods from OllamaService and adds tracking.
    """
    
    async def generate_with_tracking(
        self,
        prompt: str,
        db: AsyncSession,
        user_id: int,
        operation_type: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 500,
        job_id: Optional[int] = None,
        application_id: Optional[int] = None,
        endpoint: Optional[str] = None,
        rag_used: bool = False,
        rag_chunks: Optional[int] = None,
        extra_metadata: Optional[Dict] = None
    ) -> str:
        """Generate text with automatic token tracking"""
        start_time = time.time()
        success = True
        error_message = None
        completion = ""
        
        try:
            # Call parent method
            completion = await self.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            logger.info(f"Generation successful for {operation_type}")
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Generation error: {e}")
            raise
        
        finally:
            # Track token usage
            response_time_ms = (time.time() - start_time) * 1000
            
            try:
                full_prompt = f"{system_prompt}\n\n{prompt}" if system_prompt else prompt
                
                await TokenTracker.create_usage_record(
                    db=db,
                    user_id=user_id,
                    operation_type=operation_type,
                    prompt=full_prompt,
                    completion=completion,
                    model_name=self.model,
                    job_id=job_id,
                    application_id=application_id,
                    endpoint=endpoint,
                    rag_used=rag_used,
                    rag_chunks=rag_chunks,
                    response_time_ms=response_time_ms,
                    success=success,
                    error_message=error_message,
                    extra_metadata=extra_metadata
                )
            except Exception as track_error:
                logger.error(f"Error tracking tokens: {track_error}")
        
        return completion
    
    async def chat_with_tracking(
        self,
        messages: List[Dict[str, str]],
        db: AsyncSession,
        user_id: int,
        operation_type: str = "chat",
        temperature: float = 0.7,
        max_tokens: int = 500,
        job_id: Optional[int] = None,
        application_id: Optional[int] = None,
        endpoint: Optional[str] = None,
        rag_used: bool = False,
        rag_chunks: Optional[int] = None,
        extra_metadata: Optional[Dict] = None
    ) -> str:
        """Chat with automatic token tracking"""
        start_time = time.time()
        success = True
        error_message = None
        completion = ""
        
        try:
            # Call parent method
            completion = await self.chat(
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            logger.info(f"Chat successful for {operation_type}")
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Chat error: {e}")
            raise
        
        finally:
            # Track token usage
            response_time_ms = (time.time() - start_time) * 1000
            
            try:
                # Build prompt from messages
                full_prompt = "\n".join([f"{msg['role']}: {msg['content']}" for msg in messages])
                
                await TokenTracker.create_usage_record(
                    db=db,
                    user_id=user_id,
                    operation_type=operation_type,
                    prompt=full_prompt,
                    completion=completion,
                    model_name=self.model,
                    job_id=job_id,
                    application_id=application_id,
                    endpoint=endpoint,
                    rag_used=rag_used,
                    rag_chunks=rag_chunks,
                    response_time_ms=response_time_ms,
                    success=success,
                    error_message=error_message,
                    extra_metadata=extra_metadata
                )
            except Exception as track_error:
                logger.error(f"Error tracking tokens: {track_error}")
        
        return completion
    
    async def answer_job_question_with_tracking(
        self,
        question: str,
        user_profile: Dict,
        job_details: Dict,
        db: AsyncSession,
        user_id: int,
        job_id: Optional[int] = None,
        application_id: Optional[int] = None,
        rag_chunks: Optional[int] = None
    ) -> str:
        """Answer job question with tracking"""
        start_time = time.time()
        success = True
        error_message = None
        answer = ""
        
        try:
            # Call parent method
            answer = await self.answer_job_question(
                question=question,
                user_profile=user_profile,
                job_details=job_details
            )
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Question answering error: {e}")
            raise
        
        finally:
            response_time_ms = (time.time() - start_time) * 1000
            
            try:
                # Build context for tracking
                context = self._build_user_context(user_profile)
                prompt = f"Question: {question}\n\nContext: {context[:500]}"
                
                await TokenTracker.create_usage_record(
                    db=db,
                    user_id=user_id,
                    operation_type="question_answer",
                    prompt=prompt,
                    completion=answer,
                    model_name=self.model,
                    job_id=job_id,
                    application_id=application_id,
                    endpoint="/ai/answer-question",
                    rag_used=(rag_chunks is not None and rag_chunks > 0),
                    rag_chunks=rag_chunks,
                    response_time_ms=response_time_ms,
                    success=success,
                    error_message=error_message,
                    extra_metadata={"question": question}
                )
            except Exception as track_error:
                logger.error(f"Error tracking tokens: {track_error}")
        
        return answer
    
    async def generate_cover_letter_with_tracking(
        self,
        user_profile: Dict,
        job_details: Dict,
        db: AsyncSession,
        user_id: int,
        job_id: Optional[int] = None,
        template: Optional[str] = None,
        rag_used: bool = False,
        rag_chunks: Optional[int] = None
    ) -> str:
        """Generate cover letter with tracking"""
        start_time = time.time()
        success = True
        error_message = None
        cover_letter = ""
        
        try:
            # Call parent method
            cover_letter = await self.generate_cover_letter(
                user_profile=user_profile,
                job_details=job_details,
                template=template
            )
            
        except Exception as e:
            success = False
            error_message = str(e)
            logger.error(f"Cover letter error: {e}")
            raise
        
        finally:
            response_time_ms = (time.time() - start_time) * 1000
            
            try:
                context = self._build_user_context(user_profile)
                prompt = f"Job: {job_details.get('title')} at {job_details.get('company')}\n\nProfile: {context[:500]}"
                
                await TokenTracker.create_usage_record(
                    db=db,
                    user_id=user_id,
                    operation_type="cover_letter_generation",
                    prompt=prompt,
                    completion=cover_letter,
                    model_name=self.model,
                    job_id=job_id,
                    endpoint="/ai/generate-cover-letter",
                    rag_used=rag_used,
                    rag_chunks=rag_chunks,
                    response_time_ms=response_time_ms,
                    success=success,
                    error_message=error_message,
                    extra_metadata={
                        "job_title": job_details.get('title'),
                        "company": job_details.get('company')
                    }
                )
            except Exception as track_error:
                logger.error(f"Error tracking tokens: {track_error}")
        
        return cover_letter


# Create singleton instance
ollama_tracker = OllamaServiceWithTracking()