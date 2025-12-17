from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_base"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Resume/Profile data
    full_name = Column(String, nullable=True)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    location = Column(String, nullable=True)
    linkedin_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    
    # Professional summary
    summary = Column(Text, nullable=True)
    
    # Structured data (stored as JSON)
    work_experience = Column(JSON, nullable=True)  # List of work experiences
    education = Column(JSON, nullable=True)  # List of education entries
    skills = Column(JSON, nullable=True)  # List of skills
    certifications = Column(JSON, nullable=True)  # List of certifications
    projects = Column(JSON, nullable=True)  # List of projects
    
    # Application preferences
    preferences = Column(JSON, nullable=True)  # Salary, remote preference, etc.
    
    # Common Q&A
    qa_pairs = Column(JSON, nullable=True)  # Pre-answered common questions
    
    # Resume files
    resume_path = Column(String, nullable=True)
    cover_letter_template = Column(Text, nullable=True)
    
    # Vector embeddings reference (for RAG)
    embedding_id = Column(String, nullable=True)  # Reference to Qdrant collection
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="knowledge_base")

    def __repr__(self):
        return f"<KnowledgeBase(id={self.id}, user_id={self.user_id})>"
