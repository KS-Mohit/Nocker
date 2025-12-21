"""
Response Evaluation API Endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.evaluation import (
    ResponseEvaluationCreate,
    ResponseEvaluationResponse,
    EvaluationStats,
    AutoEvaluationRequest
)
from app.services.evaluator.response_evaluator import ResponseEvaluator
from app.models.token_usage import TokenUsage
from sqlalchemy import select

router = APIRouter()


@router.post("/manual", response_model=ResponseEvaluationResponse)
async def create_manual_evaluation(
    evaluation: ResponseEvaluationCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a manual evaluation for an AI response.
    
    Use this after reviewing a response to rate its quality.
    """
    try:
        result = await ResponseEvaluator.create_evaluation(db, evaluation)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-keyword", response_model=ResponseEvaluationResponse)
async def auto_evaluate_keyword(
    request: AutoEvaluationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-evaluate response based on keyword matching.
    
    Checks if the response contains expected keywords.
    """
    try:
        # Get the token usage record
        result = await db.execute(
            select(TokenUsage).where(TokenUsage.id == request.token_usage_id)
        )
        token_usage = result.scalar_one_or_none()
        
        if not token_usage:
            raise HTTPException(status_code=404, detail="Token usage record not found")
        
        # Get the response text from completion_text field
        response_text = token_usage.completion_text if token_usage.completion_text else ""
        
        evaluation = await ResponseEvaluator.auto_evaluate_keyword_match(
            db=db,
            token_usage_id=request.token_usage_id,
            user_id=token_usage.user_id,
            expected_keywords=request.expected_keywords or [],
            response_text=response_text
        )
        
        return evaluation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-llm", response_model=ResponseEvaluationResponse)
async def auto_evaluate_llm(
    request: AutoEvaluationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Auto-evaluate response using another LLM call.
    
    The LLM judges the quality of the response.
    This costs tokens but provides detailed evaluation.
    """
    try:
        # Get the token usage record
        result = await db.execute(
            select(TokenUsage).where(TokenUsage.id == request.token_usage_id)
        )
        token_usage = result.scalar_one_or_none()
        
        if not token_usage:
            raise HTTPException(status_code=404, detail="Token usage record not found")
        
        # Extract question from prompt_text (simplified - might need better parsing)
        question = token_usage.prompt_text.split("Question:")[-1].split("\n")[0] if token_usage.prompt_text and "Question:" in token_usage.prompt_text else (token_usage.prompt_text[:200] if token_usage.prompt_text else "Unknown question")
        response_text = token_usage.completion_text if token_usage.completion_text else ""
        
        evaluation = await ResponseEvaluator.auto_evaluate_with_llm(
            db=db,
            token_usage_id=request.token_usage_id,
            user_id=token_usage.user_id,
            question=question,
            response_text=response_text,
            context=request.context
        )
        
        return evaluation
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats", response_model=EvaluationStats)
async def get_evaluation_statistics(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated evaluation statistics.
    
    Shows average scores across all evaluations.
    """
    try:
        stats = await ResponseEvaluator.get_evaluation_stats(db, user_id, operation_type)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{token_usage_id}", response_model=list[ResponseEvaluationResponse])
async def get_evaluations_for_response(
    token_usage_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all evaluations for a specific response.
    
    A response can have multiple evaluations (manual + auto).
    """
    try:
        from app.models.response_evaluation import ResponseEvaluation
        
        result = await db.execute(
            select(ResponseEvaluation).where(ResponseEvaluation.token_usage_id == token_usage_id)
        )
        evaluations = result.scalars().all()
        return evaluations
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))