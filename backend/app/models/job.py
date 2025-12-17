from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.db.base import Base


class JobStatus(str, enum.Enum):
    PENDING = "pending"
    SCRAPED = "scraped"
    READY = "ready"
    APPLIED = "applied"
    FAILED = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Job details
    url = Column(String, nullable=False)
    title = Column(String, nullable=True)
    company = Column(String, nullable=True)
    location = Column(String, nullable=True)
    job_type = Column(String, nullable=True)  # Full-time, Part-time, Contract, etc.
    workplace_type = Column(String, nullable=True)  # Remote, Hybrid, On-site
    description = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    
    # Metadata
    status = Column(SQLEnum(JobStatus, native_enum=False), default=JobStatus.PENDING)
    scraped_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Job(id={self.id}, title={self.title}, company={self.company})>"
