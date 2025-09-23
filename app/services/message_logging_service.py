"""
High-performance message logging service with batch processing
"""
import asyncio
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from collections import deque
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database.models import MessageLog, User
from app.models.schemas import Message
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MessageLoggingService:
    """
    High-performance message logging service with batch processing
    
    Features:
    - Batch processing for high throughput
    - Memory-based queue with configurable flush intervals
    - Automatic overflow protection
    - Concurrent-safe operations
    """
    
    def __init__(self):
        self.message_queue: deque = deque()
        self.batch_size = 50
        self.flush_interval_seconds = 600  # 10 minutes
        self.max_queue_size = 1000  # Prevent memory overflow
        self.overflow_flush_interval = 120  # 2 minutes for overflow
        
        self._flush_task = None
        self._lock = asyncio.Lock()
        self._running = False
    
    async def start(self):
        """Start the background batch processing task"""
        if self._running:
            return
        
        self._running = True
        self._flush_task = asyncio.create_task(self._batch_flush_worker())
        logger.info("Message logging service started")
    
    async def stop(self):
        """Stop the background task and flush remaining messages"""
        if not self._running:
            return
        
        self._running = False
        
        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass
        
        # Flush remaining messages
        await self._flush_batch()
        logger.info("Message logging service stopped")
    
    async def log_message(
        self,
        session: AsyncSession,
        user: User,
        model: str,
        request_messages: List[Message],
        response_message: Optional[Message] = None,
        research_enabled: bool = False,
        r_type: Optional[str] = None,
        tokens_used: int = 0,
        processing_time_ms: int = 0,
        ip_address: Optional[str] = None
    ):
        """
        Log a message conversation
        
        This method adds the message to a queue for batch processing
        """
        
        try:
            # Prepare message data
            messages_data = {
                "request": [{"role": msg.role, "content": msg.content} for msg in request_messages],
                "response": {
                    "role": response_message.role,
                    "content": response_message.content
                } if response_message else None
            }
            
            # Create log entry
            log_entry = {
                "user_id": user.id,
                "username": user.username,
                "email": user.email,
                "model": model,
                "messages": messages_data,
                "research_enabled": research_enabled,
                "r_type": r_type,
                "tokens_used": tokens_used,
                "processing_time_ms": processing_time_ms,
                "ip_address": ip_address,
                "timestamp": datetime.now()
            }
            
            # Add to queue
            async with self._lock:
                self.message_queue.append(log_entry)
                
                # Check for overflow
                if len(self.message_queue) >= self.max_queue_size:
                    logger.warning(f"Message queue overflow detected ({len(self.message_queue)} messages)")
                    # Trigger immediate flush in background
                    asyncio.create_task(self._flush_batch())
            
        except Exception as e:
            logger.error(f"Failed to queue message log: {e}")
            # Fallback to direct database write
            try:
                await self._write_message_direct(session, log_entry)
            except Exception as e2:
                logger.error(f"Failed to write message log directly: {e2}")
    
    async def _batch_flush_worker(self):
        """Background worker for batch flushing"""
        while self._running:
            try:
                # Wait for flush interval or until stopped
                await asyncio.sleep(self.flush_interval_seconds)
                
                # Check if we need to flush due to queue size
                async with self._lock:
                    queue_size = len(self.message_queue)
                
                if queue_size >= self.batch_size:
                    await self._flush_batch()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in batch flush worker: {e}")
                await asyncio.sleep(10)  # Wait before retrying
    
    async def _flush_batch(self):
        """Flush queued messages to database"""
        if not self.message_queue:
            return
        
        try:
            # Get batch of messages to flush
            async with self._lock:
                batch = []
                while self.message_queue and len(batch) < self.batch_size:
                    batch.append(self.message_queue.popleft())
            
            if not batch:
                return
            
            # Write batch to database
            from app.database.database import get_db_session
            
            async with get_db_session() as session:
                message_logs = []
                
                for entry in batch:
                    message_log = MessageLog(
                        user_id=entry["user_id"],
                        username=entry["username"],
                        email=entry["email"],
                        model=entry["model"],
                        messages=entry["messages"],
                        research_enabled=entry["research_enabled"],
                        r_type=entry["r_type"],
                        tokens_used=entry["tokens_used"],
                        processing_time_ms=entry["processing_time_ms"],
                        ip_address=entry["ip_address"],
                        timestamp=entry["timestamp"]
                    )
                    message_logs.append(message_log)
                
                session.add_all(message_logs)
                await session.commit()
                
                logger.info(f"Flushed {len(batch)} message logs to database")
        
        except Exception as e:
            logger.error(f"Failed to flush message batch: {e}")
            
            # Re-queue failed messages (at the front)
            async with self._lock:
                for entry in reversed(batch):
                    self.message_queue.appendleft(entry)
    
    async def _write_message_direct(self, session: AsyncSession, log_entry: dict):
        """Write message log directly to database (fallback)"""
        try:
            message_log = MessageLog(
                user_id=log_entry["user_id"],
                username=log_entry["username"],
                email=log_entry["email"],
                model=log_entry["model"],
                messages=log_entry["messages"],
                research_enabled=log_entry["research_enabled"],
                r_type=log_entry["r_type"],
                tokens_used=log_entry["tokens_used"],
                processing_time_ms=log_entry["processing_time_ms"],
                ip_address=log_entry["ip_address"],
                timestamp=log_entry["timestamp"]
            )
            
            session.add(message_log)
            await session.commit()
            
        except Exception as e:
            logger.error(f"Failed to write message log directly: {e}")
            await session.rollback()
    
    async def get_user_messages(
        self,
        session: AsyncSession,
        user_id: int,
        page: int = 1,
        page_size: int = 50,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get message logs for a specific user"""
        
        try:
            # Build query
            query = select(MessageLog).where(MessageLog.user_id == user_id)
            
            if start_date:
                query = query.where(MessageLog.timestamp >= start_date)
            if end_date:
                query = query.where(MessageLog.timestamp <= end_date)
            
            # Get total count
            count_query = select(func.count()).select_from(
                query.subquery()
            )
            total_result = await session.execute(count_query)
            total_count = total_result.scalar()
            
            # Apply pagination and ordering
            query = query.order_by(MessageLog.timestamp.desc())
            query = query.offset((page - 1) * page_size).limit(page_size)
            
            # Execute query
            result = await session.execute(query)
            messages = result.scalars().all()
            
            return {
                "messages": messages,
                "total_count": total_count,
                "page": page,
                "page_size": page_size,
                "total_pages": (total_count + page_size - 1) // page_size
            }
            
        except Exception as e:
            logger.error(f"Failed to get user messages: {e}")
            return {
                "messages": [],
                "total_count": 0,
                "page": page,
                "page_size": page_size,
                "total_pages": 0
            }
    
    async def get_message_statistics(
        self,
        session: AsyncSession,
        user_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Get message statistics"""
        
        try:
            # Build base query
            query = select(MessageLog)
            
            if user_id:
                query = query.where(MessageLog.user_id == user_id)
            if start_date:
                query = query.where(MessageLog.timestamp >= start_date)
            if end_date:
                query = query.where(MessageLog.timestamp <= end_date)
            
            # Get all messages for statistics
            result = await session.execute(query)
            messages = result.scalars().all()
            
            # Calculate statistics
            total_messages = len(messages)
            total_tokens = sum(msg.tokens_used for msg in messages)
            avg_processing_time = sum(msg.processing_time_ms for msg in messages) / total_messages if total_messages > 0 else 0
            
            # Group by model
            model_stats = {}
            for msg in messages:
                if msg.model not in model_stats:
                    model_stats[msg.model] = {"count": 0, "tokens": 0}
                model_stats[msg.model]["count"] += 1
                model_stats[msg.model]["tokens"] += msg.tokens_used
            
            # Group by r_type
            rtype_stats = {}
            for msg in messages:
                rtype = msg.r_type or "none"
                if rtype not in rtype_stats:
                    rtype_stats[rtype] = 0
                rtype_stats[rtype] += 1
            
            return {
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "average_processing_time_ms": avg_processing_time,
                "messages_with_research": sum(1 for msg in messages if msg.research_enabled),
                "model_statistics": model_stats,
                "rtype_statistics": rtype_stats
            }
            
        except Exception as e:
            logger.error(f"Failed to get message statistics: {e}")
            return {
                "total_messages": 0,
                "total_tokens": 0,
                "average_processing_time_ms": 0,
                "messages_with_research": 0,
                "model_statistics": {},
                "rtype_statistics": {}
            }
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        return {
            "queue_size": len(self.message_queue),
            "max_queue_size": self.max_queue_size,
            "batch_size": self.batch_size,
            "flush_interval_seconds": self.flush_interval_seconds,
            "is_running": self._running
        }


# Global service instance
message_logging_service = MessageLoggingService()