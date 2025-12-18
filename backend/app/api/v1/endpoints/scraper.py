from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from app.models.knowledge_base import KnowledgeBase

from app.api.deps import get_db
from app.models.job import Job
from app.services.browser.linkedin_scraper import LinkedInScraper
from app.services.ai.ollama_tracker import ollama_tracker

router = APIRouter()


class ScrapeJobRequest(BaseModel):
    job_url: str
    save_screenshot: bool = True


@router.post("/scrape")
async def scrape_job_endpoint(
    request: ScrapeJobRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scrape job details from LinkedIn URL
    """
    scraper = LinkedInScraper()
    
    try:
        job_data = await scraper.scrape_job(request.job_url, save_screenshot=request.save_screenshot)
        
        db_job = Job(
            user_id=1,
            url=request.job_url,
            title=job_data.get('title'),
            company=job_data.get('company'),
            location=job_data.get('location'),
            workplace_type=job_data.get('workplace_type'),
            job_type=job_data.get('job_type'),
            description=job_data.get('description'),
            status='scraped'
        )
        
        db.add(db_job)
        await db.commit()
        await db.refresh(db_job)
        
        return {
            "success": True,
            "message": "Job scraped successfully",
            "job": {
                "id": db_job.id,
                "title": db_job.title,
                "company": db_job.company,
                "location": db_job.location
            },
            "screenshot": job_data.get('screenshot_path') if request.save_screenshot else None
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scrape-and-prepare")
async def scrape_and_prepare(
    request: ScrapeJobRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Scrape job and generate cover letter with token tracking
    """
    scraper = LinkedInScraper()
    
    try:
        # 1. Scrape job
        job_data = await scraper.scrape_job(request.job_url, save_screenshot=False)
        
        # 2. Save job to database
        db_job = Job(
            user_id=1,
            url=request.job_url,
            title=job_data.get('title'),
            company=job_data.get('company'),
            location=job_data.get('location'),
            workplace_type=job_data.get('workplace_type'),
            job_type=job_data.get('job_type'),
            description=job_data.get('description'),
            status='scraped'
        )
        
        db.add(db_job)
        await db.commit()
        await db.refresh(db_job)
        
        # 3. Get user's knowledge base
        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
        )
        kb = kb_result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=404,
                detail="Knowledge base not found. Please upload your resume first."
            )
        
        # 4. Prepare data for cover letter
        user_profile = {
            "full_name": kb.full_name,
            "summary": kb.summary,
            "work_experience": kb.work_experience,
            "skills": kb.skills,
            "education": kb.education
        }
        
        job_details = {
            "title": db_job.title,
            "company": db_job.company,
            "location": db_job.location,
            "description": db_job.description
        }
        
        # 5. Generate cover letter WITH TRACKING
        cover_letter = await ollama_tracker.generate_cover_letter_with_tracking(
            user_profile=user_profile,
            job_details=job_details,
            db=db,
            user_id=1,
            job_id=db_job.id,
            rag_used=False  # Set True if using RAG for cover letter
        )
        
        return {
            "success": True,
            "job": {
                "id": db_job.id,
                "title": db_job.title,
                "company": db_job.company,
                "location": db_job.location
            },
            "cover_letter": cover_letter
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    
@router.post("/auto-apply")
async def auto_apply_to_job(
    request: ScrapeJobRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Automatically apply to a LinkedIn job using Easy Apply with token tracking
    """
    from app.services.browser.form_filler import LinkedInFormFiller
    from app.models.application import Application
    
    form_filler = LinkedInFormFiller()
    
    try:
        # 1. Get user's knowledge base
        kb_result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
        )
        kb = kb_result.scalar_one_or_none()
        
        if not kb:
            raise HTTPException(
                status_code=404,
                detail="Knowledge base not found. Please upload your resume first."
            )
        
        # 2. Check if job exists in database
        job_result = await db.execute(
            select(Job).where(Job.url == request.job_url)
        )
        job = job_result.scalar_one_or_none()
        
        if not job:
            # Scrape job details first
            scraper = LinkedInScraper()
            job_data = await scraper.scrape_job(request.job_url, save_screenshot=False)
            
            job = Job(
                user_id=1,
                url=request.job_url,
                title=job_data.get('title'),
                company=job_data.get('company'),
                location=job_data.get('location'),
                workplace_type=job_data.get('workplace_type'),
                job_type=job_data.get('job_type'),
                description=job_data.get('description'),
                status='scraped'
            )
            db.add(job)
            await db.commit()
            await db.refresh(job)
        
        # 3. Prepare user profile
        user_profile = {
            "full_name": kb.full_name,
            "email": kb.email,
            "phone": kb.phone,
            "location": kb.location,
            "linkedin_url": kb.linkedin_url,
            "portfolio_url": kb.portfolio_url,
            "summary": kb.summary,
            "work_experience": kb.work_experience,
            "skills": kb.skills,
            "education": kb.education,
            "certifications": kb.certifications,
            "projects": kb.projects,
            "qa_pairs": kb.qa_pairs
        }
        
        job_details = {
            "title": job.title,
            "company": job.company,
            "description": job.description
        }
        
        # 4. Generate cover letter WITH TRACKING first
        cover_letter = await ollama_tracker.generate_cover_letter_with_tracking(
            user_profile=user_profile,
            job_details=job_details,
            db=db,
            user_id=1,
            job_id=job.id,
            rag_used=False
        )
        
        # 5. Apply to job (form filler will use ollama_tracker internally)
        result = await form_filler.apply_to_job(
            job_url=request.job_url,
            user_profile=user_profile,
            job_details=job_details
        )
        
        if not result['success']:
            raise HTTPException(status_code=400, detail=result.get('error'))
        
        # 6. Save application
        application = Application(
            user_id=1,
            job_id=job.id,
            status='pending',
            cover_letter=cover_letter,
            form_responses=result.get('form_responses'),
        )
        
        db.add(application)
        job.status = 'applied'
        
        await db.commit()
        await db.refresh(application)
        
        return {
            "success": True,
            "message": "Application completed (not submitted - testing mode)",
            "job": {
                "id": job.id,
                "title": job.title,
                "company": job.company
            },
            "application": {
                "id": application.id,
                "status": application.status,
                "cover_letter": cover_letter,
                "form_responses": result.get('form_responses')
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))