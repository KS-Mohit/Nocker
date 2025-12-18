"""
Token Usage API Endpoints
Provides endpoints for viewing and analyzing token usage
"""
from typing import List, Optional
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.schemas.token_usage import (
    TokenUsageResponse,
    TokenUsageStats,
    TokenUsageFilter,
    TokenBudget,
    TokenUsageAlert
)
from app.services.tracker.token_tracker import TokenTracker
from app.models.token_usage import TokenUsage
from sqlalchemy import select, and_

router = APIRouter()


@router.get("/recent", response_model=List[TokenUsageResponse])
async def get_recent_usage(
    user_id: int = Query(1, description="User ID"),
    limit: int = Query(10, ge=1, le=100, description="Number of recent records"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get recent token usage records for a user.
    
    Returns the most recent token usage records with detailed information.
    """
    try:
        usage_records = await TokenTracker.get_recent_usage(db, user_id, limit)
        return usage_records
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching usage: {str(e)}")


@router.get("/stats", response_model=TokenUsageStats)
async def get_usage_statistics(
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    job_id: Optional[int] = Query(None, description="Filter by job ID"),
    application_id: Optional[int] = Query(None, description="Filter by application ID"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    start_date: Optional[datetime] = Query(None, description="Start date for filtering"),
    end_date: Optional[datetime] = Query(None, description="End date for filtering"),
    success: Optional[bool] = Query(None, description="Filter by success status"),
    rag_used: Optional[bool] = Query(None, description="Filter by RAG usage"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get aggregated token usage statistics.
    
    Returns comprehensive statistics including:
    - Total tokens used
    - Average tokens per operation
    - Breakdown by operation type
    - RAG vs non-RAG comparison
    - Success rate
    - Response time metrics
    """
    try:
        filters = TokenUsageFilter(
            user_id=user_id,
            job_id=job_id,
            application_id=application_id,
            operation_type=operation_type,
            start_date=start_date,
            end_date=end_date,
            success=success,
            rag_used=rag_used
        )
        stats = await TokenTracker.get_usage_stats(db, filters)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating stats: {str(e)}")


@router.get("/daily-stats", response_model=TokenUsageStats)
async def get_daily_statistics(
    user_id: int = Query(1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get token usage statistics for today.
    """
    try:
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end = today_start + timedelta(days=1)
        
        filters = TokenUsageFilter(
            user_id=user_id,
            start_date=today_start,
            end_date=today_end
        )
        stats = await TokenTracker.get_usage_stats(db, filters)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating daily stats: {str(e)}")


@router.get("/monthly-stats", response_model=TokenUsageStats)
async def get_monthly_statistics(
    user_id: int = Query(1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get token usage statistics for this month.
    """
    try:
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        filters = TokenUsageFilter(
            user_id=user_id,
            start_date=month_start
        )
        stats = await TokenTracker.get_usage_stats(db, filters)
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error calculating monthly stats: {str(e)}")


@router.get("/by-operation", response_model=List[dict])
async def get_usage_by_operation(
    user_id: int = Query(1, description="User ID"),
    start_date: Optional[datetime] = Query(None, description="Start date"),
    end_date: Optional[datetime] = Query(None, description="End date"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get token usage breakdown by operation type.
    
    Returns a list of operation types with their token usage.
    """
    try:
        filters = TokenUsageFilter(
            user_id=user_id,
            start_date=start_date,
            end_date=end_date
        )
        stats = await TokenTracker.get_usage_stats(db, filters)
        
        # Format as list of dicts
        result = []
        for op_type, token_count in stats.tokens_by_type.items():
            result.append({
                "operation_type": op_type,
                "total_tokens": token_count,
                "operations_count": stats.operations_by_type.get(op_type, 0),
                "avg_tokens": token_count / stats.operations_by_type.get(op_type, 1)
            })
        
        # Sort by total tokens descending
        result.sort(key=lambda x: x["total_tokens"], reverse=True)
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting operation breakdown: {str(e)}")


@router.get("/rag-comparison", response_model=dict)
async def get_rag_comparison(
    user_id: int = Query(1, description="User ID"),
    operation_type: Optional[str] = Query(None, description="Filter by operation type"),
    db: AsyncSession = Depends(get_db)
):
    """
    Compare token usage between RAG and non-RAG operations.
    
    Shows the efficiency gains from using RAG.
    """
    try:
        # Get stats with RAG
        rag_filters = TokenUsageFilter(user_id=user_id, rag_used=True, operation_type=operation_type)
        rag_stats = await TokenTracker.get_usage_stats(db, rag_filters)
        
        # Get stats without RAG
        non_rag_filters = TokenUsageFilter(user_id=user_id, rag_used=False, operation_type=operation_type)
        non_rag_stats = await TokenTracker.get_usage_stats(db, non_rag_filters)
        
        # Calculate savings
        rag_avg = rag_stats.avg_tokens_per_operation
        non_rag_avg = non_rag_stats.avg_tokens_per_operation
        
        savings_percentage = 0.0
        if non_rag_avg > 0:
            savings_percentage = ((non_rag_avg - rag_avg) / non_rag_avg) * 100
        
        return {
            "rag_operations": {
                "count": rag_stats.total_operations,
                "total_tokens": rag_stats.total_tokens,
                "avg_tokens": rag_avg,
                "avg_response_time_ms": rag_stats.avg_response_time_ms
            },
            "non_rag_operations": {
                "count": non_rag_stats.total_operations,
                "total_tokens": non_rag_stats.total_tokens,
                "avg_tokens": non_rag_avg,
                "avg_response_time_ms": non_rag_stats.avg_response_time_ms
            },
            "comparison": {
                "token_savings_percentage": round(savings_percentage, 2),
                "avg_tokens_saved_per_operation": round(non_rag_avg - rag_avg, 2),
                "recommendation": "Use RAG for better efficiency" if savings_percentage > 0 else "RAG may not be beneficial for this operation"
            }
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error comparing RAG usage: {str(e)}")


@router.post("/check-budget", response_model=List[TokenUsageAlert])
async def check_budget(
    budget: TokenBudget,
    user_id: int = Query(1, description="User ID"),
    db: AsyncSession = Depends(get_db)
):
    """
    Check if user is approaching or exceeding token budget limits.
    
    Returns alerts if limits are being approached or exceeded.
    """
    try:
        alerts = await TokenTracker.check_budget_limits(
            db=db,
            user_id=user_id,
            daily_limit=budget.daily_limit,
            monthly_limit=budget.monthly_limit
        )
        return alerts
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error checking budget: {str(e)}")


@router.get("/timeline", response_model=List[dict])
async def get_usage_timeline(
    user_id: int = Query(1, description="User ID"),
    days: int = Query(7, ge=1, le=90, description="Number of days to show"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get daily token usage timeline for the past N days.
    
    Returns daily aggregated token usage.
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)
        
        query = select(TokenUsage).where(
            and_(
                TokenUsage.user_id == user_id,
                TokenUsage.created_at >= start_date
            )
        ).order_by(TokenUsage.created_at)
        
        result = await db.execute(query)
        records = result.scalars().all()
        
        # Group by day
        daily_usage = {}
        for record in records:
            day = record.created_at.date().isoformat()
            if day not in daily_usage:
                daily_usage[day] = {
                    "date": day,
                    "total_tokens": 0,
                    "operations": 0,
                    "rag_operations": 0,
                    "non_rag_operations": 0
                }
            
            daily_usage[day]["total_tokens"] += record.total_tokens
            daily_usage[day]["operations"] += 1
            if record.rag_used == 'true':
                daily_usage[day]["rag_operations"] += 1
            else:
                daily_usage[day]["non_rag_operations"] += 1
        
        # Convert to sorted list
        timeline = sorted(daily_usage.values(), key=lambda x: x["date"])
        return timeline
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error getting timeline: {str(e)}")


@router.delete("/clear-old", response_model=dict)
async def clear_old_records(
    days_to_keep: int = Query(90, ge=1, description="Keep records from last N days"),
    user_id: Optional[int] = Query(None, description="User ID (optional, None = all users)"),
    db: AsyncSession = Depends(get_db)
):
    """
    Delete token usage records older than N days.
    
    Useful for database maintenance.
    """
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        
        # Build delete query
        query = select(TokenUsage).where(TokenUsage.created_at < cutoff_date)
        if user_id:
            query = query.where(TokenUsage.user_id == user_id)
        
        result = await db.execute(query)
        records_to_delete = result.scalars().all()
        
        count = len(records_to_delete)
        
        for record in records_to_delete:
            await db.delete(record)
        
        await db.commit()
        
        return {
            "message": f"Deleted {count} records older than {days_to_keep} days",
            "deleted_count": count,
            "cutoff_date": cutoff_date.isoformat()
        }
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error clearing records: {str(e)}")