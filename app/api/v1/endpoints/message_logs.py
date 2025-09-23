"""
Message Logs API Endpoints for Users
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, Dict, Any
import logging

from app.models.user_schemas import (
    MessageLogEntry, MessageLogQuery, PaginatedResponse, StandardResponse
)
from app.services.message_logging_service import message_logging_service
from app.api.v1.endpoints.user_management import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/logs", tags=["Message Logs"])


@router.get("/my-messages")
async def get_my_message_logs(
    limit: int = Query(100, ge=1, le=1000, description="Number of logs to retrieve"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get current user's message logs"""
    try:
        logs = message_logging_service.get_user_message_logs(
            current_user['username'], limit, offset
        )
        
        # Get total count for pagination
        with message_logging_service.db.get_cursor() as cursor:
            cursor.execute(
                "SELECT COUNT(*) FROM message_logs WHERE username = ?",
                (current_user['username'],)
            )
            total = cursor.fetchone()[0]
        
        return PaginatedResponse(
            success=True,
            data=logs,
            total=total,
            limit=limit,
            offset=offset,
            has_more=offset + len(logs) < total
        )
        
    except Exception as e:
        logger.error(f"Get message logs error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/my-messages/{log_id}")
async def get_message_log_details(
    log_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Get detailed message log"""
    try:
        log_details = message_logging_service.get_message_log_details(
            log_id, current_user['username']
        )
        
        if not log_details:
            raise HTTPException(status_code=404, detail="Message log not found")
        
        return {
            "success": True,
            "data": log_details
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get message log details error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/stats")
async def get_my_message_stats(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Get current user's message statistics"""
    try:
        with message_logging_service.db.get_cursor() as cursor:
            username = current_user['username']
            
            # Total messages
            cursor.execute("SELECT COUNT(*) FROM message_logs WHERE username = ?", (username,))
            total_messages = cursor.fetchone()[0]
            
            # Messages this month
            cursor.execute("""
                SELECT COUNT(*) FROM message_logs 
                WHERE username = ? AND date(time) >= date('now', 'start of month')
            """, (username,))
            messages_this_month = cursor.fetchone()[0]
            
            # Total tokens used
            cursor.execute("""
                SELECT SUM(tokens_used) FROM message_logs 
                WHERE username = ? AND tokens_used > 0
            """, (username,))
            total_tokens = cursor.fetchone()[0] or 0
            
            # Average processing time
            cursor.execute("""
                SELECT AVG(processing_time_ms) FROM message_logs 
                WHERE username = ? AND processing_time_ms > 0
            """, (username,))
            avg_processing_time = cursor.fetchone()[0] or 0
            
            # Most used models
            cursor.execute("""
                SELECT model, COUNT(*) as count 
                FROM message_logs 
                WHERE username = ?
                GROUP BY model 
                ORDER BY count DESC 
                LIMIT 5
            """, (username,))
            top_models = [{"model": row[0], "count": row[1]} for row in cursor.fetchall()]
            
            return {
                "success": True,
                "data": {
                    "total_messages": total_messages,
                    "messages_this_month": messages_this_month,
                    "total_tokens_used": total_tokens,
                    "average_processing_time_ms": round(avg_processing_time, 2),
                    "top_models": top_models
                }
            }
            
    except Exception as e:
        logger.error(f"Get message stats error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/buffer-status")
async def get_logging_buffer_status():
    """Get current logging buffer status (for monitoring)"""
    try:
        status = message_logging_service.get_buffer_status()
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        logger.error(f"Get buffer status error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")