"""
Token Tracking Service
Handles token counting and usage tracking for all AI operations
"""
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from loguru import logger

from app.models.token_usage import TokenUsage
from app.schemas.token_usage import (
    TokenUsageCreate,
    TokenUsageStats,
    TokenUsageFilter,
    TokenUsageAlert
)


class TokenTracker:
    """Service for tracking token usage"""
    
    @staticmethod
    def estimate_tokens(text: str) -> int:
        """
        Estimate token count for a given text.
        Using approximate ratio of 1 token = 4 characters for English text.
        This is a rough estimate - actual tokenization may vary.
        
        For more accurate counting, we'll use tiktoken when available.
        """
        if not text:
            return 0
        
        # Rule of thumb: ~4 characters per token for English
        # Adjust based on your model's tokenizer
        return len(text) // 4
    
    @staticmethod
    async def create_usage_record(
        db: AsyncSession,
        user_id: int,
        operation_type: str,
        prompt: str,
        completion: str,
        model_name: str = "llama3",
        job_id: Optional[int] = None,
        application_id: Optional[int] = None,
        endpoint: Optional[str] = None,
        rag_used: bool = False,
        rag_chunks: Optional[int] = None,
        response_time_ms: Optional[float] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> TokenUsage:
        """
        Create a token usage record.
        
        Args:
            db: Database session
            user_id: User ID
            operation_type: Type of operation (chat, rag_answer, cover_letter, etc.)
            prompt: The prompt text sent to AI
            completion: The completion text received from AI
            model_name: Model used
            job_id: Associated job ID (optional)
            application_id: Associated application ID (optional)
            endpoint: API endpoint that triggered this (optional)
            rag_used: Whether RAG was used
            rag_chunks: Number of RAG chunks retrieved
            response_time_ms: Response time in milliseconds
            success: Whether operation succeeded
            error_message: Error message if failed
            metadata: Additional metadata
            
        Returns:
            TokenUsage object
        """
        try:
            # Estimate token counts
            prompt_tokens = TokenTracker.estimate_tokens(prompt)
            completion_tokens = TokenTracker.estimate_tokens(completion)
            total_tokens = prompt_tokens + completion_tokens
            
            # Calculate cost (example rates - adjust based on your model)
            # Ollama is free, but tracking for future paid APIs
            cost_per_1k_tokens = 0.0  # $0 for Ollama
            estimated_cost = (total_tokens / 1000) * cost_per_1k_tokens
            
            # Create record
            usage = TokenUsage(
                user_id=user_id,
                job_id=job_id,
                application_id=application_id,
                operation_type=operation_type,
                endpoint=endpoint,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                rag_used='true' if rag_used else 'false',
                rag_chunks_retrieved=rag_chunks,
                context_length=len(prompt),
                response_time_ms=response_time_ms,
                success='true' if success else 'false',
                error_message=error_message,
                estimated_cost=estimated_cost,
                extra_metadata=extra_metadata
            )
            
            db.add(usage)
            await db.commit()
            await db.refresh(usage)
            
            logger.info(
                f"Token usage tracked: {operation_type} - "
                f"{total_tokens} tokens ({prompt_tokens} prompt + {completion_tokens} completion)"
            )
            
            return usage
            
        except Exception as e:
            logger.error(f"Error creating token usage record: {e}")
            await db.rollback()
            raise
    
    @staticmethod
    async def get_usage_stats(
        db: AsyncSession,
        filters: TokenUsageFilter
    ) -> TokenUsageStats:
        """
        Get aggregated token usage statistics.
        
        Args:
            db: Database session
            filters: Filter parameters
            
        Returns:
            TokenUsageStats object
        """
        try:
            # Build base query
            query = select(TokenUsage)
            
            # Apply filters
            conditions = []
            if filters.user_id:
                conditions.append(TokenUsage.user_id == filters.user_id)
            if filters.job_id:
                conditions.append(TokenUsage.job_id == filters.job_id)
            if filters.application_id:
                conditions.append(TokenUsage.application_id == filters.application_id)
            if filters.operation_type:
                conditions.append(TokenUsage.operation_type == filters.operation_type)
            if filters.start_date:
                conditions.append(TokenUsage.created_at >= filters.start_date)
            if filters.end_date:
                conditions.append(TokenUsage.created_at <= filters.end_date)
            if filters.success is not None:
                success_str = 'true' if filters.success else 'false'
                conditions.append(TokenUsage.success == success_str)
            if filters.rag_used is not None:
                rag_str = 'true' if filters.rag_used else 'false'
                conditions.append(TokenUsage.rag_used == rag_str)
            
            if conditions:
                query = query.where(and_(*conditions))
            
            # Execute query
            result = await db.execute(query)
            records = result.scalars().all()
            
            if not records:
                return TokenUsageStats(
                    total_tokens=0,
                    total_operations=0,
                    avg_tokens_per_operation=0.0,
                    total_prompt_tokens=0,
                    total_completion_tokens=0,
                    total_cost=0.0,
                    operations_by_type={},
                    tokens_by_type={},
                    rag_operations=0,
                    non_rag_operations=0,
                    success_rate=0.0,
                    avg_response_time_ms=None
                )
            
            # Calculate statistics
            total_tokens = sum(r.total_tokens for r in records)
            total_prompt_tokens = sum(r.prompt_tokens for r in records)
            total_completion_tokens = sum(r.completion_tokens for r in records)
            total_cost = sum(r.estimated_cost or 0.0 for r in records)
            total_operations = len(records)
            
            # Operations by type
            operations_by_type: Dict[str, int] = {}
            tokens_by_type: Dict[str, int] = {}
            for record in records:
                op_type = record.operation_type
                operations_by_type[op_type] = operations_by_type.get(op_type, 0) + 1
                tokens_by_type[op_type] = tokens_by_type.get(op_type, 0) + record.total_tokens
            
            # RAG statistics
            rag_operations = sum(1 for r in records if r.rag_used == 'true')
            non_rag_operations = total_operations - rag_operations
            
            # Success rate
            successful_operations = sum(1 for r in records if r.success == 'true')
            success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0.0
            
            # Average response time
            response_times = [r.response_time_ms for r in records if r.response_time_ms is not None]
            avg_response_time_ms = sum(response_times) / len(response_times) if response_times else None
            
            return TokenUsageStats(
                total_tokens=total_tokens,
                total_operations=total_operations,
                avg_tokens_per_operation=total_tokens / total_operations if total_operations > 0 else 0.0,
                total_prompt_tokens=total_prompt_tokens,
                total_completion_tokens=total_completion_tokens,
                total_cost=total_cost,
                operations_by_type=operations_by_type,
                tokens_by_type=tokens_by_type,
                rag_operations=rag_operations,
                non_rag_operations=non_rag_operations,
                success_rate=success_rate,
                avg_response_time_ms=avg_response_time_ms
            )
            
        except Exception as e:
            logger.error(f"Error getting usage stats: {e}")
            raise
    
    @staticmethod
    async def check_budget_limits(
        db: AsyncSession,
        user_id: int,
        daily_limit: Optional[int] = None,
        monthly_limit: Optional[int] = None
    ) -> List[TokenUsageAlert]:
        """
        Check if user is approaching or exceeding token budget limits.
        
        Args:
            db: Database session
            user_id: User ID to check
            daily_limit: Daily token limit (optional)
            monthly_limit: Monthly token limit (optional)
            
        Returns:
            List of alerts if limits are approached/exceeded
        """
        alerts = []
        
        try:
            # Check daily limit
            if daily_limit:
                today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                daily_query = select(func.sum(TokenUsage.total_tokens)).where(
                    and_(
                        TokenUsage.user_id == user_id,
                        TokenUsage.created_at >= today_start
                    )
                )
                result = await db.execute(daily_query)
                daily_usage = result.scalar() or 0
                
                if daily_usage >= daily_limit:
                    alerts.append(TokenUsageAlert(
                        alert_type="daily_limit_exceeded",
                        current_usage=daily_usage,
                        limit=daily_limit,
                        percentage=(daily_usage / daily_limit) * 100,
                        message=f"Daily token limit exceeded: {daily_usage}/{daily_limit} tokens used"
                    ))
                elif daily_usage >= daily_limit * 0.8:
                    alerts.append(TokenUsageAlert(
                        alert_type="daily_limit_warning",
                        current_usage=daily_usage,
                        limit=daily_limit,
                        percentage=(daily_usage / daily_limit) * 100,
                        message=f"Approaching daily limit: {daily_usage}/{daily_limit} tokens used"
                    ))
            
            # Check monthly limit
            if monthly_limit:
                month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
                monthly_query = select(func.sum(TokenUsage.total_tokens)).where(
                    and_(
                        TokenUsage.user_id == user_id,
                        TokenUsage.created_at >= month_start
                    )
                )
                result = await db.execute(monthly_query)
                monthly_usage = result.scalar() or 0
                
                if monthly_usage >= monthly_limit:
                    alerts.append(TokenUsageAlert(
                        alert_type="monthly_limit_exceeded",
                        current_usage=monthly_usage,
                        limit=monthly_limit,
                        percentage=(monthly_usage / monthly_limit) * 100,
                        message=f"Monthly token limit exceeded: {monthly_usage}/{monthly_limit} tokens used"
                    ))
                elif monthly_usage >= monthly_limit * 0.8:
                    alerts.append(TokenUsageAlert(
                        alert_type="monthly_limit_warning",
                        current_usage=monthly_usage,
                        limit=monthly_limit,
                        percentage=(monthly_usage / monthly_limit) * 100,
                        message=f"Approaching monthly limit: {monthly_usage}/{monthly_limit} tokens used"
                    ))
            
            return alerts
            
        except Exception as e:
            logger.error(f"Error checking budget limits: {e}")
            return []
    
    @staticmethod
    async def get_recent_usage(
        db: AsyncSession,
        user_id: int,
        limit: int = 10
    ) -> List[TokenUsage]:
        """
        Get recent token usage records for a user.
        
        Args:
            db: Database session
            user_id: User ID
            limit: Number of records to return
            
        Returns:
            List of TokenUsage objects
        """
        try:
            query = (
                select(TokenUsage)
                .where(TokenUsage.user_id == user_id)
                .order_by(TokenUsage.created_at.desc())
                .limit(limit)
            )
            result = await db.execute(query)
            return result.scalars().all()
        except Exception as e:
            logger.error(f"Error getting recent usage: {e}")
            raise


# Decorator for automatic token tracking
def track_tokens(operation_type: str):
    """
    Decorator to automatically track token usage for AI operations.
    
    Usage:
        @track_tokens("cover_letter_generation")
        async def generate_cover_letter(prompt: str, db: AsyncSession):
            # your code here
            return completion
    """
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            
            try:
                # Execute function
                result = await func(*args, **kwargs)
                
                # Calculate response time
                response_time_ms = (time.time() - start_time) * 1000
                
                # Track usage (you'll need to extract prompt/completion from result)
                # This is a template - customize based on your needs
                
                return result
                
            except Exception as e:
                logger.error(f"Error in {func.__name__}: {e}")
                raise
        
        return wrapper
    return decorator