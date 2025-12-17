from sentence_transformers import SentenceTransformer
from typing import List, Union
from loguru import logger
import numpy as np


class EmbeddingService:
    """Generate embeddings using sentence-transformers"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """
        Initialize embedding model
        
        Args:
            model_name: HuggingFace model name
                - all-MiniLM-L6-v2: Fast, 384 dimensions (recommended)
                - all-mpnet-base-v2: Better quality, 768 dimensions (slower)
        """
        logger.info(f"Loading embedding model: {model_name}")
        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        logger.info(f"Model loaded. Embedding dimension: {self.dimension}")
    
    def encode(self, text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
        """
        Generate embeddings for text
        
        Args:
            text: Single string or list of strings
            
        Returns:
            Embedding vector(s)
        """
        try:
            if isinstance(text, str):
                # Single text
                embedding = self.model.encode(text, convert_to_numpy=True)
                return embedding.tolist()
            else:
                # Batch of texts
                embeddings = self.model.encode(text, convert_to_numpy=True)
                return embeddings.tolist()
                
        except Exception as e:
            logger.error(f"Embedding error: {e}")
            raise
    
    def encode_work_experience(self, experience: dict) -> List[float]:
        """
        Generate embedding for work experience
        Combines title, company, and description
        """
        text_parts = []
        
        if experience.get('title'):
            text_parts.append(f"Title: {experience['title']}")
        
        if experience.get('company'):
            text_parts.append(f"Company: {experience['company']}")
        
        if experience.get('description'):
            text_parts.append(f"Description: {experience['description']}")
        
        if experience.get('technologies'):
            tech_list = ', '.join(experience['technologies'])
            text_parts.append(f"Technologies: {tech_list}")
        
        text = ' | '.join(text_parts)
        return self.encode(text)
    
    def encode_project(self, project: dict) -> List[float]:
        """Generate embedding for project"""
        text_parts = []
        
        if project.get('name'):
            text_parts.append(f"Project: {project['name']}")
        
        if project.get('description'):
            text_parts.append(f"Description: {project['description']}")
        
        if project.get('technologies'):
            tech_list = ', '.join(project['technologies'])
            text_parts.append(f"Technologies: {tech_list}")
        
        text = ' | '.join(text_parts)
        return self.encode(text)
    
    def encode_skill(self, skill: Union[str, dict]) -> List[float]:
        """Generate embedding for skill"""
        if isinstance(skill, str):
            text = f"Skill: {skill}"
        else:
            text = f"Skill: {skill.get('skill', skill.get('name', ''))}"
            if skill.get('proficiency'):
                text += f" | Proficiency: {skill['proficiency']}"
        
        return self.encode(text)
    
    def encode_qa_pair(self, question: str, answer: str = None) -> List[float]:
        """Generate embedding for Q&A pair"""
        if answer:
            text = f"Question: {question} | Answer: {answer}"
        else:
            text = f"Question: {question}"
        
        return self.encode(text)
    
    def similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """
        Calculate cosine similarity between two embeddings
        
        Returns:
            Similarity score (0-1, higher = more similar)
        """
        vec1 = np.array(embedding1)
        vec2 = np.array(embedding2)
        
        # Cosine similarity
        similarity = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return float(similarity)


# Global instance (singleton pattern)
_embedding_service = None

def get_embedding_service() -> EmbeddingService:
    """Get or create embedding service instance"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service