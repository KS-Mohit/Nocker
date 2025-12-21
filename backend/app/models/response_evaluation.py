"""
Response Evaluation Model
Tracks quality metrics for AI responses
"""
from datetime import datetime
from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship

from app.db.base import Base


class ResponseEvaluation(Base):
    """Evaluation of AI-generated responses"""
    __tablename__ = "response_evaluations"

    id = Column(Integer, primary_key=True, index=True)
    token_usage_id = Column(Integer, ForeignKey("token_usage.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Scores (1-5 scale)
    relevance_score = Column(Float, nullable=True)
    accuracy_score = Column(Float, nullable=True)
    completeness_score = Column(Float, nullable=True)
    conciseness_score = Column(Float, nullable=True)
    professionalism_score = Column(Float, nullable=True)
    overall_score = Column(Float, nullable=False)
    
    # Evaluation metadata
    evaluation_method = Column(String(50), nullable=False)  # manual, auto_llm, auto_keyword, etc.
    evaluator_notes = Column(Text, nullable=True)
    expected_answer = Column(Text, nullable=True)
    
    # Quality flags
    needs_improvement = Column(Boolean, default=False)
    is_hallucination = Column(Boolean, default=False)
    is_inappropriate = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    token_usage = relationship("TokenUsage", backref="evaluations")
    user = relationship("User", backref="response_evaluations")

    def __repr__(self):
        return f"<ResponseEvaluation {self.id} - Score: {self.overall_score}>"