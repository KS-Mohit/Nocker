"""
Token Usage Schemas
Request/Response models for token tracking
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class TokenUsageBase(BaseModel):
    """Base schema for token usage"""
    operation_type: str = Field(..., description="Type of operation")
    model_name: str = Field(default="llama3", description="AI model used")
    prompt_tokens: int = Field(default=0, description="Tokens in prompt")
    completion_tokens: int = Field(default=0, description="Tokens in completion")
    total_tokens: int = Field(default=0, description="Total tokens")


class TokenUsageCreate(TokenUsageBase):
    """Schema for creating token usage record"""
    user_id: int
    job_id: Optional[int] = None
    application_id: Optional[int] = None
    endpoint: Optional[str] = None
    rag_used: Optional[bool] = None
    rag_chunks_retrieved: Optional[int] = None
    context_length: Optional[int] = None
    response_time_ms: Optional[float] = None
    success: bool = True
    error_message: Optional[str] = None
    estimated_cost: Optional[float] = 0.0
    extra_metadata: Optional[Dict[str, Any]] = None


class TokenUsageResponse(TokenUsageBase):
    """Schema for token usage response"""
    id: int
    user_id: int
    job_id: Optional[int] = None
    application_id: Optional[int] = None
    endpoint: Optional[str] = None
    rag_used: Optional[bool] = None
    rag_chunks_retrieved: Optional[int] = None
    context_length: Optional[int] = None
    response_time_ms: Optional[float] = None
    success: bool
    error_message: Optional[str] = None
    estimated_cost: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenUsageStats(BaseModel):
    """Aggregated token usage statistics"""
    total_tokens: int
    total_operations: int
    avg_tokens_per_operation: float
    total_prompt_tokens: int
    total_completion_tokens: int
    total_cost: float
    operations_by_type: Dict[str, int]
    tokens_by_type: Dict[str, int]
    rag_operations: int
    non_rag_operations: int
    success_rate: float
    avg_response_time_ms: Optional[float] = None


class TokenUsageFilter(BaseModel):
    """Filter parameters for queries"""
    user_id: Optional[int] = None
    job_id: Optional[int] = None
    application_id: Optional[int] = None
    operation_type: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    success: Optional[bool] = None
    rag_used: Optional[bool] = None
    skip: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=1000)


class TokenBudget(BaseModel):
    """Token budget settings"""
    daily_limit: Optional[int] = None
    monthly_limit: Optional[int] = None
    per_operation_limit: Optional[int] = None
    alert_threshold: float = Field(default=0.8)


class TokenUsageAlert(BaseModel):
    """Alert for budget limits"""
    alert_type: str
    current_usage: int
    limit: int
    percentage: float
    message: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)