from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, 
    VectorParams, 
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue
)
from typing import List, Dict, Optional
from loguru import logger
import uuid

from app.core.config import settings


class QdrantService:
    """Service for interacting with Qdrant vector database"""
    
    COLLECTION_EXPERIENCES = "work_experiences"
    COLLECTION_PROJECTS = "projects"
    COLLECTION_SKILLS = "skills"
    COLLECTION_QA = "qa_pairs"
    
    def __init__(self):
        """Initialize Qdrant client"""
        self.client = QdrantClient(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT
        )
        logger.info(f"Connected to Qdrant at {settings.QDRANT_HOST}:{settings.QDRANT_PORT}")
    
    def create_collections(self, vector_size: int = 384):
        """
        Create all collections if they don't exist
        
        Args:
            vector_size: Embedding dimension (384 for all-MiniLM-L6-v2)
        """
        collections = [
            self.COLLECTION_EXPERIENCES,
            self.COLLECTION_PROJECTS,
            self.COLLECTION_SKILLS,
            self.COLLECTION_QA
        ]
        
        for collection_name in collections:
            try:
                # Check if collection exists
                self.client.get_collection(collection_name)
                logger.info(f"Collection '{collection_name}' already exists")
            except Exception:
                # Create collection
                self.client.create_collection(
                    collection_name=collection_name,
                    vectors_config=VectorParams(
                        size=vector_size,
                        distance=Distance.COSINE
                    )
                )
                logger.info(f"✨ Created collection '{collection_name}'")
    
    def delete_collection(self, collection_name: str):
        """Delete a collection"""
        try:
            self.client.delete_collection(collection_name)
            logger.info(f"Deleted collection '{collection_name}'")
        except Exception as e:
            logger.warning(f"Could not delete collection '{collection_name}': {e}")
    
    def upsert_work_experience(
        self,
        kb_id: int,
        experience_id: str,
        vector: List[float],
        payload: Dict
    ):
        """Store work experience embedding"""
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                **payload,
                "kb_id": kb_id,
                "experience_id": experience_id,
                "type": "work_experience"
            }
        )
        
        self.client.upsert(
            collection_name=self.COLLECTION_EXPERIENCES,
            points=[point]
        )
        logger.info(f"Stored work experience: {payload.get('title', 'Unknown')}")
    
    def upsert_project(
        self,
        kb_id: int,
        project_id: str,
        vector: List[float],
        payload: Dict
    ):
        """Store project embedding"""
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                **payload,
                "kb_id": kb_id,
                "project_id": project_id,
                "type": "project"
            }
        )
        
        self.client.upsert(
            collection_name=self.COLLECTION_PROJECTS,
            points=[point]
        )
        logger.info(f"Stored project: {payload.get('name', 'Unknown')}")
    
    def upsert_skill(
        self,
        kb_id: int,
        skill_id: str,
        vector: List[float],
        payload: Dict
    ):
        """Store skill embedding"""
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                **payload,
                "kb_id": kb_id,
                "skill_id": skill_id,
                "type": "skill"
            }
        )
        
        self.client.upsert(
            collection_name=self.COLLECTION_SKILLS,
            points=[point]
        )
        logger.info(f"Stored skill: {payload.get('skill', 'Unknown')}")
    
    def upsert_qa_pair(
        self,
        kb_id: int,
        qa_id: str,
        vector: List[float],
        payload: Dict
    ):
        """Store Q&A pair embedding"""
        point = PointStruct(
            id=str(uuid.uuid4()),
            vector=vector,
            payload={
                **payload,
                "kb_id": kb_id,
                "qa_id": qa_id,
                "type": "qa"
            }
        )
        
        self.client.upsert(
            collection_name=self.COLLECTION_QA,
            points=[point]
        )
        logger.info(f"Stored Q&A: {payload.get('question', 'Unknown')[:50]}...")
    
    def search_experiences(
        self,
        query_vector: List[float],
        kb_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """
        Search for relevant work experiences
        
        Args:
            query_vector: Question/query embedding
            kb_id: User's knowledge base ID
            limit: Number of results
            
        Returns:
            List of matching experiences with scores
        """
        results = self.client.query_points(
            collection_name=self.COLLECTION_EXPERIENCES,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="kb_id",
                        match=MatchValue(value=kb_id)
                    )
                ]
            ),
            limit=limit
        ).points
        
        return [
            {
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    
    def search_projects(
        self,
        query_vector: List[float],
        kb_id: int,
        limit: int = 5
    ) -> List[Dict]:
        """Search for relevant projects"""
        results = self.client.query_points(
            collection_name=self.COLLECTION_PROJECTS,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="kb_id",
                        match=MatchValue(value=kb_id)
                    )
                ]
            ),
            limit=limit
        ).points
        
        return [
            {
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    
    def search_skills(
        self,
        query_vector: List[float],
        kb_id: int,
        limit: int = 10
    ) -> List[Dict]:
        """Search for relevant skills"""
        results = self.client.query_points(
            collection_name=self.COLLECTION_SKILLS,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="kb_id",
                        match=MatchValue(value=kb_id)
                    )
                ]
            ),
            limit=limit
        ).points
        
        return [
            {
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    
    def search_qa_pairs(
        self,
        query_vector: List[float],
        kb_id: int,
        limit: int = 3
    ) -> List[Dict]:
        """Search for similar Q&A pairs"""
        results = self.client.query_points(
            collection_name=self.COLLECTION_QA,
            query=query_vector,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="kb_id",
                        match=MatchValue(value=kb_id)
                    )
                ]
            ),
            limit=limit
        ).points
        
        return [
            {
                "score": result.score,
                "payload": result.payload
            }
            for result in results
        ]
    
    def delete_by_kb_id(self, kb_id: int):
        """Delete all vectors for a knowledge base"""
        collections = [
            self.COLLECTION_EXPERIENCES,
            self.COLLECTION_PROJECTS,
            self.COLLECTION_SKILLS,
            self.COLLECTION_QA
        ]
        
        for collection in collections:
            try:
                self.client.delete(
                    collection_name=collection,
                    points_selector=Filter(
                        must=[
                            FieldCondition(
                                key="kb_id",
                                match=MatchValue(value=kb_id)
                            )
                        ]
                    )
                )
                logger.info(f"Deleted vectors from '{collection}' for kb_id={kb_id}")
            except Exception as e:
                logger.warning(f"Could not delete from '{collection}': {e}")


# Global instance
_qdrant_service = None

def get_qdrant_service() -> QdrantService:
    """Get or create Qdrant service instance"""
    global _qdrant_service
    if _qdrant_service is None:
        _qdrant_service = QdrantService()
    return _qdrant_service