from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class ApplicationStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    ACCEPTED = "accepted"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    
    # Application details
    status = Column(SQLEnum(ApplicationStatus), default=ApplicationStatus.PENDING)
    cover_letter = Column(Text, nullable=True)
    resume_used = Column(String, nullable=True)  # Path or ID of resume used
    
    # Form responses (store as JSON)
    form_responses = Column(JSON, nullable=True)
    
    # Tracking
    applied_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    screenshot_path = Column(String, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")

    def __repr__(self):
        return f"<Application(id={self.id}, job_id={self.job_id}, status={self.status})>"
