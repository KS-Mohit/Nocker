from typing import Dict, List
from loguru import logger

from app.services.embeddings.embedding_service import get_embedding_service
from app.services.qdrant.qdrant_service import get_qdrant_service


class RAGService:
    """Retrieval Augmented Generation Service"""
    
    def __init__(self):
        self.embedding_service = get_embedding_service()
        self.qdrant_service = get_qdrant_service()
    
    def index_knowledge_base(self, kb_id: int, knowledge_base: Dict):
        """
        Index entire knowledge base into Qdrant
        
        Args:
            kb_id: Knowledge base ID
            knowledge_base: Dict with work_experience, projects, skills, qa_pairs
        """
        logger.info(f"Indexing knowledge base {kb_id}...")
        
        # 1. Index work experiences
        work_experiences = knowledge_base.get('work_experience', [])
        for idx, exp in enumerate(work_experiences):
            try:
                vector = self.embedding_service.encode_work_experience(exp)
                self.qdrant_service.upsert_work_experience(
                    kb_id=kb_id,
                    experience_id=f"exp_{idx}",
                    vector=vector,
                    payload=exp
                )
            except Exception as e:
                logger.error(f"Error indexing experience {idx}: {e}")
        
        # 2. Index projects
        projects = knowledge_base.get('projects', [])
        for idx, proj in enumerate(projects):
            try:
                vector = self.embedding_service.encode_project(proj)
                self.qdrant_service.upsert_project(
                    kb_id=kb_id,
                    project_id=f"proj_{idx}",
                    vector=vector,
                    payload=proj
                )
            except Exception as e:
                logger.error(f"Error indexing project {idx}: {e}")
        
        # 3. Index skills
        skills = knowledge_base.get('skills', [])
        for idx, skill in enumerate(skills):
            try:
                vector = self.embedding_service.encode_skill(skill)
                skill_payload = {"skill": skill} if isinstance(skill, str) else skill
                self.qdrant_service.upsert_skill(
                    kb_id=kb_id,
                    skill_id=f"skill_{idx}",
                    vector=vector,
                    payload=skill_payload
                )
            except Exception as e:
                logger.error(f"Error indexing skill {idx}: {e}")
        
        # 4. Index Q&A pairs
        qa_pairs = knowledge_base.get('qa_pairs', {})
        for idx, (question, answer) in enumerate(qa_pairs.items()):
            try:
                vector = self.embedding_service.encode_qa_pair(question, answer)
                self.qdrant_service.upsert_qa_pair(
                    kb_id=kb_id,
                    qa_id=f"qa_{idx}",
                    vector=vector,
                    payload={"question": question, "answer": answer}
                )
            except Exception as e:
                logger.error(f"Error indexing Q&A {idx}: {e}")
        
        logger.info(f"Indexed {len(work_experiences)} experiences, {len(projects)} projects, {len(skills)} skills, {len(qa_pairs)} Q&As")
    
    def retrieve_relevant_context(
        self,
        question: str,
        kb_id: int,
        max_experiences: int = 3,
        max_projects: int = 2,
        max_skills: int = 5
    ) -> Dict:
        """
        Retrieve relevant context for answering a question
        
        Args:
            question: The question to answer
            kb_id: User's knowledge base ID
            max_experiences: Max work experiences to retrieve
            max_projects: Max projects to retrieve
            max_skills: Max skills to retrieve
            
        Returns:
            Dict with relevant experiences, projects, skills
        """
        logger.info(f"Retrieving context for: {question[:50]}...")
        
        # Generate query embedding
        query_vector = self.embedding_service.encode(question)
        
        # Search across collections
        experiences = self.qdrant_service.search_experiences(
            query_vector=query_vector,
            kb_id=kb_id,
            limit=max_experiences
        )
        
        projects = self.qdrant_service.search_projects(
            query_vector=query_vector,
            kb_id=kb_id,
            limit=max_projects
        )
        
        skills = self.qdrant_service.search_skills(
            query_vector=query_vector,
            kb_id=kb_id,
            limit=max_skills
        )
        
        qa_pairs = self.qdrant_service.search_qa_pairs(
            query_vector=query_vector,
            kb_id=kb_id,
            limit=2
        )
        
        logger.info(f"Retrieved {len(experiences)} experiences, {len(projects)} projects, {len(skills)} skills, {len(qa_pairs)} Q&As")
        
        return {
            "experiences": experiences,
            "projects": projects,
            "skills": skills,
            "qa_pairs": qa_pairs
        }
    
    def build_context_string(self, retrieved_context: Dict) -> str:
        """
        Build a context string from retrieved items for LLM
        """
        context_parts = []
        
        # Experiences
        if retrieved_context.get('experiences'):
            context_parts.append("Relevant Work Experience:")
            for item in retrieved_context['experiences']:
                exp = item['payload']
                score = item['score']
                context_parts.append(f"- {exp.get('title')} at {exp.get('company')} (relevance: {score:.2f})")
                context_parts.append(f"  {exp.get('description', '')[:200]}")
        
        # Projects
        if retrieved_context.get('projects'):
            context_parts.append("\nRelevant Projects:")
            for item in retrieved_context['projects']:
                proj = item['payload']
                score = item['score']
                context_parts.append(f"- {proj.get('name')} (relevance: {score:.2f})")
                context_parts.append(f"  {proj.get('description', '')[:200]}")
        
        # Skills
        if retrieved_context.get('skills'):
            skills_list = [item['payload'].get('skill', '') for item in retrieved_context['skills']]
            context_parts.append(f"\nRelevant Skills: {', '.join(skills_list[:10])}")
        
        # Previous Q&As
        if retrieved_context.get('qa_pairs'):
            context_parts.append("\nSimilar Questions You've Answered:")
            for item in retrieved_context['qa_pairs']:
                qa = item['payload']
                context_parts.append(f"Q: {qa.get('question')}")
                context_parts.append(f"A: {qa.get('answer', '')[:150]}")
        
        return "\n".join(context_parts)
    
    def delete_knowledge_base(self, kb_id: int):
        """Delete all indexed data for a knowledge base"""
        logger.info(f"Deleting knowledge base {kb_id} from Qdrant...")
        self.qdrant_service.delete_by_kb_id(kb_id)
        logger.info(f"Deleted knowledge base {kb_id}")


# Global instance
_rag_service = None

def get_rag_service() -> RAGService:
    """Get or create RAG service instance"""
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service