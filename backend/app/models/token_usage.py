"""
Token Usage Tracking Model
Tracks token consumption for all AI interactions
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Float
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base import Base


class TokenUsage(Base):
    """Track token usage for all AI operations"""
    __tablename__ = "token_usage"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    
    # Operation details
    operation_type = Column(String, nullable=False, index=True)
    endpoint = Column(String, nullable=True)
    model_name = Column(String, nullable=False)
    
    # Token counts
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    total_tokens = Column(Integer, nullable=False, default=0)
    
    # Store actual text for evaluation
    prompt_text = Column(Text, nullable=True)
    completion_text = Column(Text, nullable=True)
    
    # Context information
    rag_used = Column(String, nullable=True)
    rag_chunks_retrieved = Column(Integer, nullable=True)
    context_length = Column(Integer, nullable=True)
    
    # Performance metrics
    response_time_ms = Column(Float, nullable=True)
    success = Column(String, nullable=False, default='true')
    error_message = Column(Text, nullable=True)
    
    # Cost tracking
    estimated_cost = Column(Float, nullable=True, default=0.0)
    
    # Additional metadata
    extra_metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="token_usage")
    job = relationship("Job", backref="token_usage")
    application = relationship("Application", backref="token_usage")

    def __repr__(self):
        return f"<TokenUsage {self.operation_type} - {self.total_tokens} tokens>"