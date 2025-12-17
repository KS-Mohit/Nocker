from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import json

from app.api.deps import get_db
from app.models.knowledge_base import KnowledgeBase
from app.schemas.knowledge_base import (
    KnowledgeBaseCreate,
    KnowledgeBaseUpdate,
    KnowledgeBaseResponse
)
from app.services.parsers.resume_parser import ResumeParser, parse_resume_with_ai
from app.services.ai.ollama_service import OllamaService

router = APIRouter()


@router.post("/upload-resume", response_model=dict)
async def upload_resume(
    file: UploadFile = File(...),
    use_ai_parsing: bool = True,
    auto_index: bool = True,  # NEW PARAMETER
    db: AsyncSession = Depends(get_db)
):
    """
    Upload resume PDF and create/update knowledge base
    
    Args:
        file: PDF file
        use_ai_parsing: Use AI for better parsing (slower but more accurate)
        auto_index: Automatically index into Qdrant for RAG (recommended)
    """
    # Validate file type
    if not file.filename.endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")
    
    try:
        # Read PDF
        pdf_bytes = await file.read()
        
        # Parse PDF
        parser = ResumeParser()
        resume_text = parser.extract_text_from_pdf(pdf_bytes)
        
        if use_ai_parsing:
            # Use AI for accurate parsing
            ollama = OllamaService()
            try:
                parsed_data = await parse_resume_with_ai(resume_text, ollama)
            finally:
                await ollama.close()
        else:
            # Use regex parsing (faster but less accurate)
            parsed_data = {
                "full_name": parser.extract_name(resume_text),
                "email": parser.extract_email(resume_text),
                "phone": parser.extract_phone(resume_text),
                "summary": None,
                "work_experience": [],
                "education": [],
                "skills": parser.extract_skills_section(resume_text),
            }
            
            # Extract URLs
            urls = parser.extract_urls(resume_text)
            parsed_data.update(urls)
        
        # Check if knowledge base exists
        result = await db.execute(
            select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
        )
        kb = result.scalar_one_or_none()
        
        if kb:
            # Update existing
            for field, value in parsed_data.items():
                if value is not None:
                    setattr(kb, field, value)
            
            await db.commit()
            await db.refresh(kb)
            message = "Knowledge base updated from resume"
        else:
            # Create new
            kb = KnowledgeBase(
                user_id=1,
                **parsed_data
            )
            db.add(kb)
            await db.commit()
            await db.refresh(kb)
            message = "Knowledge base created from resume"
        
        # ✨ NEW: Auto-index into Qdrant
        index_result = None
        if auto_index:
            try:
                from app.services.rag.rag_service import get_rag_service
                
                # Prepare data for indexing
                kb_data = {
                    "work_experience": kb.work_experience or [],
                    "projects": kb.projects or [],
                    "skills": kb.skills or [],
                    "qa_pairs": kb.qa_pairs or {}
                }
                
                # Index into Qdrant
                rag_service = get_rag_service()
                rag_service.index_knowledge_base(kb_id=kb.id, knowledge_base=kb_data)
                
                # Update embedding_id
                kb.embedding_id = f"indexed_{kb.id}"
                await db.commit()
                
                index_result = {
                    "indexed": True,
                    "experiences": len(kb_data['work_experience']),
                    "projects": len(kb_data['projects']),
                    "skills": len(kb_data['skills']),
                    "qa_pairs": len(kb_data['qa_pairs'])
                }
                
                message += " and indexed for RAG"
                
            except Exception as e:
                logger.error(f"Auto-indexing failed: {e}")
                index_result = {
                    "indexed": False,
                    "error": str(e)
                }
        
        return {
            "success": True,
            "message": message,
            "parsed_data": parsed_data,
            "knowledge_base_id": kb.id,
            "indexing": index_result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=KnowledgeBaseResponse, status_code=201)
async def create_knowledge_base(
    kb: KnowledgeBaseCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create or update user's knowledge base profile manually
    """
    # Check if knowledge base already exists for user
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
    )
    existing_kb = result.scalar_one_or_none()
    
    if existing_kb:
        raise HTTPException(
            status_code=400,
            detail="Knowledge base already exists. Use PATCH to update or upload a resume."
        )
    
    # Create new knowledge base
    db_kb = KnowledgeBase(
        user_id=1,
        **kb.model_dump()
    )
    
    db.add(db_kb)
    await db.commit()
    await db.refresh(db_kb)
    
    return db_kb


@router.get("/", response_model=KnowledgeBaseResponse)
async def get_knowledge_base(
    db: AsyncSession = Depends(get_db)
):
    """
    Get user's knowledge base profile
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found. Please upload a resume or create manually.")
    
    return kb


@router.patch("/", response_model=KnowledgeBaseResponse)
async def update_knowledge_base(
    kb_update: KnowledgeBaseUpdate,
    auto_reindex: bool = True,  # NEW PARAMETER
    db: AsyncSession = Depends(get_db)
):
    """
    Update user's knowledge base profile
    Add additional information after resume upload
    
    Args:
        kb_update: Fields to update
        auto_reindex: Automatically re-index into Qdrant after update
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(
            status_code=404, 
            detail="Knowledge base not found. Please upload a resume first."
        )
    
    # Update fields
    update_data = kb_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(kb, field, value)
    
    await db.commit()
    await db.refresh(kb)
    
    # ✨ NEW: Re-index if requested
    if auto_reindex and kb.embedding_id:
        try:
            from app.services.rag.rag_service import get_rag_service
            
            kb_data = {
                "work_experience": kb.work_experience or [],
                "projects": kb.projects or [],
                "skills": kb.skills or [],
                "qa_pairs": kb.qa_pairs or {}
            }
            
            rag_service = get_rag_service()
            rag_service.index_knowledge_base(kb_id=kb.id, knowledge_base=kb_data)
            
            logger.info(f"Re-indexed knowledge base {kb.id}")
            
        except Exception as e:
            logger.error(f"Re-indexing failed: {e}")
    
    return kb


@router.post("/add-qa", response_model=KnowledgeBaseResponse)
async def add_qa_pair(
    question: str,
    answer: str,
    auto_reindex: bool = True,  # NEW PARAMETER
    db: AsyncSession = Depends(get_db)
):
    """
    Add a Q&A pair to knowledge base for common interview questions
    
    Args:
        question: Interview question
        answer: Your answer
        auto_reindex: Automatically re-index into Qdrant
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Initialize qa_pairs if None
    if kb.qa_pairs is None:
        kb.qa_pairs = {}
    
    # Add Q&A pair
    kb.qa_pairs[question] = answer
    
    await db.commit()
    await db.refresh(kb)
    
    # ✨ NEW: Re-index if requested
    if auto_reindex and kb.embedding_id:
        try:
            from app.services.rag.rag_service import get_rag_service
            
            kb_data = {
                "work_experience": kb.work_experience or [],
                "projects": kb.projects or [],
                "skills": kb.skills or [],
                "qa_pairs": kb.qa_pairs or {}
            }
            
            rag_service = get_rag_service()
            rag_service.index_knowledge_base(kb_id=kb.id, knowledge_base=kb_data)
            
            logger.info(f"Re-indexed knowledge base {kb.id} with new Q&A")
            
        except Exception as e:
            logger.error(f"Re-indexing failed: {e}")
    
    return kb


@router.delete("/", status_code=204)
async def delete_knowledge_base(
    db: AsyncSession = Depends(get_db)
):
    """
    Delete user's knowledge base
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    await db.delete(kb)
    await db.commit()
    
    return None


@router.get("/export", response_model=dict)
async def export_knowledge_base(
    db: AsyncSession = Depends(get_db)
):
    """
    Export knowledge base as JSON for AI consumption
    """
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.user_id == 1)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Convert to dict for AI
    kb_dict = {
        "full_name": kb.full_name,
        "email": kb.email,
        "phone": kb.phone,
        "location": kb.location,
        "linkedin_url": kb.linkedin_url,
        "portfolio_url": kb.portfolio_url,
        "summary": kb.summary,
        "work_experience": kb.work_experience,
        "education": kb.education,
        "skills": kb.skills,
        "certifications": kb.certifications,
        "projects": kb.projects,
        "preferences": kb.preferences,
        "qa_pairs": kb.qa_pairs,
    }
    
    return {
        "success": True,
        "knowledge_base": kb_dict
    }