"""
Response Evaluation Service
Evaluates quality of AI-generated responses
"""
from typing import Optional, Dict, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from loguru import logger

from app.models.response_evaluation import ResponseEvaluation
from app.models.token_usage import TokenUsage
from app.schemas.evaluation import (
    ResponseEvaluationCreate,
    EvaluationStats,
    EvaluationMethod
)


class ResponseEvaluator:
    """Service for evaluating AI responses"""
    
    @staticmethod
    async def create_evaluation(
        db: AsyncSession,
        evaluation: ResponseEvaluationCreate
    ) -> ResponseEvaluation:
        """Create a manual evaluation"""
        try:
            db_evaluation = ResponseEvaluation(**evaluation.dict())
            db.add(db_evaluation)
            await db.commit()
            await db.refresh(db_evaluation)
            
            logger.info(f"Evaluation created: {db_evaluation.id} - Score: {db_evaluation.overall_score}")
            return db_evaluation
            
        except Exception as e:
            await db.rollback()
            logger.error(f"Error creating evaluation: {e}")
            raise
    
    @staticmethod
    async def auto_evaluate_keyword_match(
        db: AsyncSession,
        token_usage_id: int,
        user_id: int,
        expected_keywords: List[str],
        response_text: str
    ) -> ResponseEvaluation:
        """
        Auto-evaluate based on keyword matching.
        Checks if response contains expected keywords.
        """
        try:
            response_lower = response_text.lower()
            matched_keywords = [kw for kw in expected_keywords if kw.lower() in response_lower]
            match_percentage = len(matched_keywords) / len(expected_keywords) if expected_keywords else 0
            
            # Calculate scores
            completeness_score = 1 + (match_percentage * 4)  # 1-5 scale
            overall_score = completeness_score
            
            evaluation = ResponseEvaluationCreate(
                token_usage_id=token_usage_id,
                user_id=user_id,
                completeness_score=completeness_score,
                overall_score=overall_score,
                evaluation_method=EvaluationMethod.AUTO_KEYWORD,
                evaluator_notes=f"Matched {len(matched_keywords)}/{len(expected_keywords)} keywords",
                needs_improvement=(match_percentage < 0.5)
            )
            
            return await ResponseEvaluator.create_evaluation(db, evaluation)
            
        except Exception as e:
            logger.error(f"Error in keyword evaluation: {e}")
            raise
    
    @staticmethod
    async def auto_evaluate_with_llm(
        db: AsyncSession,
        token_usage_id: int,
        user_id: int,
        question: str,
        response_text: str,
        context: Optional[str] = None
    ) -> ResponseEvaluation:
        """
        Auto-evaluate using another LLM call.
        The LLM judges the quality of the response.
        """
        try:
            from app.services.ai.ollama_tracker import ollama_tracker
            
            # Prompt for LLM to evaluate the response
            eval_prompt = f"""Evaluate this AI response on a scale of 1-5 for each criterion:

Question: {question}
{f'Context: {context}' if context else ''}

Response to evaluate:
{response_text}

Rate the following (1-5 scale, where 5 is excellent):
1. Relevance: Does it answer the question?
2. Accuracy: Is the information correct?
3. Completeness: Does it cover all necessary points?
4. Conciseness: Is it appropriately brief without unnecessary details?
5. Professionalism: Is it well-written and professional?

Respond ONLY with JSON in this exact format:
{{
    "relevance_score": 4.5,
    "accuracy_score": 5.0,
    "completeness_score": 4.0,
    "conciseness_score": 3.5,
    "professionalism_score": 4.5,
    "overall_score": 4.3,
    "notes": "Brief explanation"
}}"""

            # Get evaluation from LLM
            eval_response = await ollama_tracker.generate_with_tracking(
                prompt=eval_prompt,
                db=db,
                user_id=user_id,
                operation_type="response_evaluation",
                system_prompt="You are an AI response evaluator. Be critical but fair.",
                temperature=0.3,  # Lower temperature for consistent scoring
                endpoint="/evaluator/auto-evaluate"
            )
            
            # Parse JSON response
            import json
            eval_response_clean = eval_response.strip()
            if eval_response_clean.startswith("```json"):
                eval_response_clean = eval_response_clean.split("```json")[1].split("```")[0]
            
            eval_data = json.loads(eval_response_clean)
            
            # Create evaluation record
            evaluation = ResponseEvaluationCreate(
                token_usage_id=token_usage_id,
                user_id=user_id,
                relevance_score=eval_data.get("relevance_score"),
                accuracy_score=eval_data.get("accuracy_score"),
                completeness_score=eval_data.get("completeness_score"),
                conciseness_score=eval_data.get("conciseness_score"),
                professionalism_score=eval_data.get("professionalism_score"),
                overall_score=eval_data.get("overall_score", 3.0),
                evaluation_method=EvaluationMethod.AUTO_LLM,
                evaluator_notes=eval_data.get("notes", ""),
                needs_improvement=(eval_data.get("overall_score", 3.0) < 3.5)
            )
            
            return await ResponseEvaluator.create_evaluation(db, evaluation)
            
        except Exception as e:
            logger.error(f"Error in LLM evaluation: {e}")
            raise
    
    @staticmethod
    async def get_evaluation_stats(
        db: AsyncSession,
        user_id: Optional[int] = None,
        operation_type: Optional[str] = None
    ) -> EvaluationStats:
        """Get aggregated evaluation statistics"""
        try:
            query = select(ResponseEvaluation)
            
            if user_id:
                query = query.where(ResponseEvaluation.user_id == user_id)
            
            if operation_type:
                query = query.join(TokenUsage).where(TokenUsage.operation_type == operation_type)
            
            result = await db.execute(query)
            evaluations = result.scalars().all()
            
            if not evaluations:
                return EvaluationStats(
                    total_evaluations=0,
                    avg_overall_score=0.0,
                    avg_relevance_score=None,
                    avg_accuracy_score=None,
                    avg_completeness_score=None,
                    avg_conciseness_score=None,
                    avg_professionalism_score=None,
                    needs_improvement_count=0,
                    hallucination_count=0,
                    inappropriate_count=0,
                    by_operation_type={},
                    by_evaluation_method={}
                )
            
            # Calculate averages
            total = len(evaluations)
            
            def safe_avg(scores):
                valid = [s for s in scores if s is not None]
                return sum(valid) / len(valid) if valid else None
            
            # Group by operation type and method
            by_op_type = {}
            by_method = {}
            
            for eval in evaluations:
                # By operation type (need to join with token_usage)
                # Simplified here - you'd fetch the operation_type from token_usage
                
                # By evaluation method
                method = eval.evaluation_method
                if method not in by_method:
                    by_method[method] = {"count": 0, "avg_score": 0}
                by_method[method]["count"] += 1
                by_method[method]["avg_score"] += eval.overall_score
            
            # Finalize averages
            for method in by_method:
                count = by_method[method]["count"]
                by_method[method]["avg_score"] = by_method[method]["avg_score"] / count if count > 0 else 0
            
            return EvaluationStats(
                total_evaluations=total,
                avg_overall_score=sum(e.overall_score for e in evaluations) / total,
                avg_relevance_score=safe_avg([e.relevance_score for e in evaluations]),
                avg_accuracy_score=safe_avg([e.accuracy_score for e in evaluations]),
                avg_completeness_score=safe_avg([e.completeness_score for e in evaluations]),
                avg_conciseness_score=safe_avg([e.conciseness_score for e in evaluations]),
                avg_professionalism_score=safe_avg([e.professionalism_score for e in evaluations]),
                needs_improvement_count=sum(1 for e in evaluations if e.needs_improvement),
                hallucination_count=sum(1 for e in evaluations if e.is_hallucination),
                inappropriate_count=sum(1 for e in evaluations if e.is_inappropriate),
                by_operation_type=by_op_type,
                by_evaluation_method=by_method
            )
            
        except Exception as e:
            logger.error(f"Error getting evaluation stats: {e}")
            raise