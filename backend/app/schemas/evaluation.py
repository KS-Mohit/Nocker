"""
Response Evaluation Schemas
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from enum import Enum


class EvaluationCriteria(str, Enum):
    """Evaluation criteria options"""
    RELEVANCE = "relevance"
    ACCURACY = "accuracy"
    COMPLETENESS = "completeness"
    CONCISENESS = "conciseness"
    PROFESSIONALISM = "professionalism"


class EvaluationMethod(str, Enum):
    """How the evaluation was performed"""
    MANUAL = "manual"  # Human review
    AUTO_LLM = "auto_llm"  # LLM judges itself
    AUTO_KEYWORD = "auto_keyword"  # Keyword matching
    AUTO_SIMILARITY = "auto_similarity"  # Semantic similarity


class ResponseEvaluationCreate(BaseModel):
    """Create evaluation for a response"""
    token_usage_id: int = Field(..., description="ID of the token usage record being evaluated")
    user_id: int
    
    # Scores (1-5 scale)
    relevance_score: Optional[float] = Field(None, ge=1, le=5)
    accuracy_score: Optional[float] = Field(None, ge=1, le=5)
    completeness_score: Optional[float] = Field(None, ge=1, le=5)
    conciseness_score: Optional[float] = Field(None, ge=1, le=5)
    professionalism_score: Optional[float] = Field(None, ge=1, le=5)
    overall_score: float = Field(..., ge=1, le=5, description="Overall quality score")
    
    # Evaluation details
    evaluation_method: EvaluationMethod
    evaluator_notes: Optional[str] = None
    expected_answer: Optional[str] = None  # For comparison
    
    # Flags
    needs_improvement: bool = False
    is_hallucination: bool = False
    is_inappropriate: bool = False


class ResponseEvaluationResponse(ResponseEvaluationCreate):
    """Response with evaluation data"""
    id: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class EvaluationStats(BaseModel):
    """Aggregated evaluation statistics"""
    total_evaluations: int
    avg_overall_score: float
    avg_relevance_score: Optional[float]
    avg_accuracy_score: Optional[float]
    avg_completeness_score: Optional[float]
    avg_conciseness_score: Optional[float]
    avg_professionalism_score: Optional[float]
    
    needs_improvement_count: int
    hallucination_count: int
    inappropriate_count: int
    
    by_operation_type: dict
    by_evaluation_method: dict


class AutoEvaluationRequest(BaseModel):
    """Request to auto-evaluate a response"""
    token_usage_id: int
    expected_keywords: Optional[list[str]] = None
    context: Optional[str] = None