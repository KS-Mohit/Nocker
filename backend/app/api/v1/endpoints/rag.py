from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional

from app.api.deps import get_db
from app.models.knowledge_base import KnowledgeBase
from app.services.rag.rag_service import get_rag_service
from app.services.ai.ollama_service import OllamaService

router = APIRouter()


class IndexKnowledgeBaseRequest(BaseModel):
    kb_id: Optional[int] = None  # If None, use current user's KB


class SearchRequest(BaseModel):
    question: str
    max_experiences: int = 3
    max_projects: int = 2
    max_skills: int = 5


class AnswerWithRAGRequest(BaseModel):
    question: str
    job_title: Optional[str] = None
    company: Optional[str] = None


@router.post("/index")
async def index_knowledge_base(
    request: IndexKnowledgeBaseRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Index knowledge base into Qdrant for semantic search
    
    This creates embeddings for:
    - Work experiences
    - Projects
    - Skills
    - Q&A pairs
    """
    kb_id = request.kb_id or 1  # Default to user 1
    
    # Get knowledge base
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    # Prepare data for indexing
    kb_data = {
        "work_experience": kb.work_experience or [],
        "projects": kb.projects or [],
        "skills": kb.skills or [],
        "qa_pairs": kb.qa_pairs or {}
    }
    
    # Index into Qdrant
    rag_service = get_rag_service()
    try:
        rag_service.index_knowledge_base(kb_id=kb_id, knowledge_base=kb_data)
        
        # Update embedding_id in database
        kb.embedding_id = f"indexed_{kb_id}"
        await db.commit()
        
        return {
            "success": True,
            "message": f"Successfully indexed knowledge base {kb_id}",
            "indexed": {
                "experiences": len(kb_data['work_experience']),
                "projects": len(kb_data['projects']),
                "skills": len(kb_data['skills']),
                "qa_pairs": len(kb_data['qa_pairs'])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/search")
async def search_knowledge_base(
    request: SearchRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Search knowledge base for relevant context
    
    Returns semantically similar:
    - Work experiences
    - Projects
    - Skills
    - Q&A pairs
    """
    kb_id = 1  # Hardcoded user
    
    # Check if KB is indexed
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    if not kb.embedding_id:
        raise HTTPException(
            status_code=400,
            detail="Knowledge base not indexed. Call /rag/index first."
        )
    
    # Search
    rag_service = get_rag_service()
    try:
        retrieved = rag_service.retrieve_relevant_context(
            question=request.question,
            kb_id=kb_id,
            max_experiences=request.max_experiences,
            max_projects=request.max_projects,
            max_skills=request.max_skills
        )
        
        return {
            "success": True,
            "question": request.question,
            "retrieved_context": retrieved
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/answer-with-rag")
async def answer_question_with_rag(
    request: AnswerWithRAGRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Answer a job application question using RAG
    
    This will:
    1. Search for relevant experiences/projects/skills
    2. Build focused context
    3. Use AI to generate answer with retrieved context
    """
    kb_id = 1  # Hardcoded user
    
    # Get knowledge base
    result = await db.execute(
        select(KnowledgeBase).where(KnowledgeBase.id == kb_id)
    )
    kb = result.scalar_one_or_none()
    
    if not kb:
        raise HTTPException(status_code=404, detail="Knowledge base not found")
    
    if not kb.embedding_id:
        raise HTTPException(
            status_code=400,
            detail="Knowledge base not indexed. Call /rag/index first."
        )
    
    # Retrieve relevant context
    rag_service = get_rag_service()
    ollama = OllamaService()
    
    try:
        # 1. Search for relevant context
        retrieved = rag_service.retrieve_relevant_context(
            question=request.question,
            kb_id=kb_id,
            max_experiences=3,
            max_projects=2,
            max_skills=5
        )
        
        # 2. Build context string
        context_str = rag_service.build_context_string(retrieved)
        
        # 3. Create enhanced prompt with retrieved context
        system_prompt = """You are a professional career advisor answering job application questions.

Use the provided relevant context from the candidate's background to craft a specific, compelling answer.

Guidelines:
- Keep answers concise (2-3 sentences)
- Reference specific experiences when relevant
- Be honest and authentic
- Show enthusiasm for the role"""

        user_prompt = f"""Question: {request.question}

{'Job: ' + request.job_title if request.job_title else ''}
{'Company: ' + request.company if request.company else ''}

Relevant Background Context:
{context_str}

Based on the above context, provide a compelling answer to the question:"""

        # 4. Generate answer
        answer = await ollama.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=0.7,
            max_tokens=300
        )
        
        return {
            "success": True,
            "question": request.question,
            "answer": answer,
            "retrieved_context": {
                "num_experiences": len(retrieved.get('experiences', [])),
                "num_projects": len(retrieved.get('projects', [])),
                "num_skills": len(retrieved.get('skills', [])),
                "num_qa_pairs": len(retrieved.get('qa_pairs', []))
            },
            "context_used": context_str[:500] + "..." if len(context_str) > 500 else context_str
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        await ollama.close()


@router.delete("/index/{kb_id}")
async def delete_index(kb_id: int):
    """
    Delete indexed knowledge base from Qdrant
    """
    rag_service = get_rag_service()
    try:
        rag_service.delete_knowledge_base(kb_id)
        return {
            "success": True,
            "message": f"Deleted index for knowledge base {kb_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))