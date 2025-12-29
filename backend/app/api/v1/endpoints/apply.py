"""
Universal Job Application API Endpoints

Supports:
- Any job application website (LinkedIn, Indeed, Glassdoor, etc.)
- Multiple LLM providers (Claude recommended, Ollama as fallback)
- RAG-enhanced responses
"""

from typing import Optional, Dict, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from loguru import logger

from app.services.mcp import get_mcp_client
from app.services.mcp.universal_form_service import (
    UniversalFormService,
    get_universal_form_service,
    JobSite
)
from app.core.config import settings


router = APIRouter(prefix="/apply", tags=["Job Applications"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ApplyRequest(BaseModel):
    """Request to apply to any job"""
    job_url: str = Field(..., description="URL of the job posting (any supported site)")
    kb_id: Optional[int] = Field(None, description="Knowledge base ID for user profile")
    
    # User profile (if kb_id not provided)
    user_profile: Optional[Dict] = Field(
        None,
        description="User profile data (alternative to kb_id)",
        json_schema_extra={
            "example": {
                "full_name": "John Doe",
                "email": "john@example.com",
                "phone": "555-1234",
                "location": "San Francisco, CA",
                "linkedin_url": "https://linkedin.com/in/johndoe",
                "summary": "Experienced software engineer...",
                "work_experience": [
                    {
                        "title": "Senior Engineer",
                        "company": "TechCorp",
                        "description": "Led development of..."
                    }
                ],
                "skills": ["Python", "React", "AWS"]
            }
        }
    )
    
    # Job details (optional, can be scraped)
    job_details: Optional[Dict] = Field(
        None,
        description="Job details (title, company, description)",
        json_schema_extra={
            "example": {
                "title": "Software Engineer",
                "company": "Google",
                "description": "We're looking for..."
            }
        }
    )
    
    # Resume path for upload
    resume_path: Optional[str] = Field(
        None,
        description="Absolute path to resume file (PDF, DOC, DOCX)",
        json_schema_extra={
            "example": "C:\\Users\\YourName\\Documents\\resume.pdf"
        }
    )
    
    # Options
    dry_run: bool = Field(
        True,
        description="If true, won't actually submit (default: true for safety)"
    )
    use_claude: bool = Field(
        True, 
        description="Use Claude API for better quality (requires ANTHROPIC_API_KEY)"
    )
    max_pages: int = Field(
        15,
        ge=1,
        le=30,
        description="Maximum form pages to process"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "job_url": "https://www.linkedin.com/jobs/view/123456789/",
                "kb_id": 1,
                "resume_path": "C:\\Users\\YourName\\Documents\\resume.pdf",
                "dry_run": True,
                "use_claude": True
            }
        }


class ApplyResponse(BaseModel):
    """Response from job application attempt"""
    success: bool
    status: str  # "submitted", "needs_review", "failed", "in_progress"
    message: str
    site_detected: Optional[str] = None
    form_responses: Optional[Dict[str, str]] = None
    pages_processed: int = 0
    screenshots: Optional[List[str]] = None
    error: Optional[str] = None


class SupportedSitesResponse(BaseModel):
    """List of supported job sites"""
    sites: List[Dict[str, str]]
    total: int


# =============================================================================
# Endpoints
# =============================================================================

@router.get("/supported-sites", response_model=SupportedSitesResponse)
async def get_supported_sites():
    """
    Get list of supported job application sites.
    
    The universal form service can work with any site, but these
    have optimized handlers for better reliability.
    """
    sites = [
        {
            "name": "LinkedIn",
            "domain": "linkedin.com",
            "type": "Easy Apply",
            "quality": "Excellent"
        },
        {
            "name": "Indeed",
            "domain": "indeed.com", 
            "type": "Indeed Apply",
            "quality": "Good"
        },
        {
            "name": "Glassdoor",
            "domain": "glassdoor.com",
            "type": "Easy Apply",
            "quality": "Good"
        },
        {
            "name": "Lever",
            "domain": "lever.co",
            "type": "ATS",
            "quality": "Good"
        },
        {
            "name": "Greenhouse",
            "domain": "greenhouse.io",
            "type": "ATS",
            "quality": "Good"
        },
        {
            "name": "Workday",
            "domain": "myworkday.com",
            "type": "ATS",
            "quality": "Experimental"
        },
        {
            "name": "Generic",
            "domain": "any",
            "type": "Universal",
            "quality": "Variable"
        }
    ]
    
    return SupportedSitesResponse(sites=sites, total=len(sites))


@router.post("/", response_model=ApplyResponse)
async def apply_to_job(request: ApplyRequest):
    """
    Apply to a job at any supported site.
    
    This endpoint:
    1. Detects the job site type (LinkedIn, Indeed, etc.)
    2. Navigates to the job posting
    3. Clicks the apply button
    4. Fills form fields using AI (Claude or Ollama)
    5. Uses RAG to retrieve relevant experience for custom questions
    6. Navigates through multi-page forms
    7. Optionally submits (if dry_run=False)
    
    **Recommended**: Use `use_claude=True` for best form understanding.
    
    **Safety**: By default, `dry_run=True` which means it will NOT
    actually submit. Set `dry_run=False` to submit for real.
    """
    # Validate input
    if not request.kb_id and not request.user_profile:
        raise HTTPException(
            status_code=400,
            detail="Either kb_id or user_profile must be provided"
        )
    
    # Get user profile
    user_profile = request.user_profile
    if request.kb_id:
        # Load from database
        from app.db.session import async_session
        from sqlalchemy import select
        from app.models.knowledge_base import KnowledgeBase
        
        async with async_session() as db:
            result = await db.execute(
                select(KnowledgeBase).where(KnowledgeBase.id == request.kb_id)
            )
            kb = result.scalar_one_or_none()
            
            if not kb:
                raise HTTPException(
                    status_code=404,
                    detail=f"Knowledge base {request.kb_id} not found"
                )
            
            user_profile = {
                "full_name": kb.full_name,
                "email": kb.email,
                "phone": kb.phone,
                "location": kb.location,
                "linkedin_url": kb.linkedin_url,
                "portfolio_url": kb.portfolio_url,
                "summary": kb.summary,
                "work_experience": kb.work_experience or [],
                "education": kb.education or [],
                "skills": kb.skills or [],
                "projects": kb.projects or [],
                "qa_pairs": kb.qa_pairs or {}
            }
    
    # Get job details
    job_details = request.job_details or {}
    if not job_details.get("title"):
        job_details["title"] = "Unknown Position"
    if not job_details.get("company"):
        job_details["company"] = "Unknown Company"
    
    # Get Claude API key from environment
    import os
    claude_api_key = os.environ.get("ANTHROPIC_API_KEY")
    
    if request.use_claude and not claude_api_key:
        logger.warning("ANTHROPIC_API_KEY not set, falling back to Ollama")
    
    # Get resume path from request or knowledge base
    resume_path = request.resume_path
    if not resume_path and user_profile.get("resume_path"):
        resume_path = user_profile.get("resume_path")
    
    # Create service
    service = UniversalFormService(
        use_claude=request.use_claude and bool(claude_api_key),
        claude_api_key=claude_api_key
    )
    
    # Apply
    result = await service.apply_to_job(
        job_url=request.job_url,
        user_profile=user_profile,
        job_details=job_details,
        kb_id=request.kb_id,
        dry_run=request.dry_run,
        max_pages=request.max_pages,
        resume_path=resume_path
    )
    
    # Determine site type
    site_name = None
    if service.current_handler:
        site_name = service.current_handler.__class__.__name__.replace("Handler", "")
    
    return ApplyResponse(
        success=result.success,
        status=result.status,
        message=result.message,
        site_detected=site_name,
        form_responses=result.form_responses,
        pages_processed=result.pages_processed,
        screenshots=result.screenshots,
        error=result.error
    )


@router.post("/preview")
async def preview_application(request: ApplyRequest):
    """
    Preview what the application would look like without applying.
    
    This navigates to the job, opens the apply form, and shows
    what fields were detected and how they would be filled.
    Does NOT submit anything.
    """
    # Force dry_run for preview
    request.dry_run = True
    return await apply_to_job(request)


@router.get("/llm-options")
async def get_llm_options():
    """
    Get information about available LLM providers for form analysis.
    """
    import os
    
    claude_available = bool(os.environ.get("ANTHROPIC_API_KEY"))
    
    return {
        "providers": [
            {
                "name": "Claude",
                "provider": "Anthropic",
                "model": "claude-sonnet-4-20250514",
                "available": claude_available,
                "quality": "Excellent",
                "cost": "~$3/1M input tokens",
                "recommendation": "Recommended for production",
                "setup": "Set ANTHROPIC_API_KEY environment variable"
            },
            {
                "name": "Ollama",
                "provider": "Local",
                "model": "llama3",
                "available": True,  # Assume available if server configured
                "quality": "Good",
                "cost": "Free",
                "recommendation": "Good for testing/development",
                "setup": "Run: ollama serve && ollama pull llama3"
            }
        ],
        "current_default": "Claude" if claude_available else "Ollama",
        "tip": "Use use_claude=True in request for best results"
    }