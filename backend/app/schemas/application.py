from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"
    REJECTED = "rejected"
    INTERVIEW = "interview"
    ACCEPTED = "accepted"


class ApplicationBase(BaseModel):
    job_id: int
    cover_letter: Optional[str] = None
    resume_used: Optional[str] = None
    form_responses: Optional[Dict[str, Any]] = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(BaseModel):
    status: Optional[ApplicationStatus] = None
    cover_letter: Optional[str] = None
    form_responses: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class ApplicationResponse(ApplicationBase):
    id: int
    user_id: int
    status: ApplicationStatus
    applied_at: Optional[datetime] = None
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True