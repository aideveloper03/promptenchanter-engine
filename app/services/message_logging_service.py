"""
High-Performance Message Logging Service with Batch Processing
"""
import json
import secrets
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from collections import deque
import threading
import time
from dataclasses import dataclass

from app.database.models import db_manager
from app.models.user_schemas import BatchMessageLog

logger = logging.getLogger(__name__)


@dataclass
class MessageLogEntry:
    """Message log entry for batch processing"""
    username: str
    email: str
    model: str
    messages: List[Dict[str, Any]]
    research_model: bool
    tokens_used: int
    processing_time_ms: int
    timestamp: datetime


class MessageLoggingService:
    """High-performance message logging with batch processing"""
    
    def __init__(self, batch_size: int = 100, batch_timeout: int = 600):  # 10 minutes default
        self.db = db_manager
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout  # seconds
        
        # In-memory buffer for high-speed logging
        self.message_buffer = deque()
        self.buffer_lock = threading.Lock()
        
        # Batch processing control
        self.batch_processor_running = False
        self.last_batch_time = time.time()
        
        # Memory management
        self.max_buffer_size = 10000  # Maximum buffer size before forcing flush
        self.memory_threshold = 1000   # Memory overflow threshold
        
        # Statistics
        self.stats = {
            'messages_logged': 0,
            'batches_processed': 0,
            'buffer_overflows': 0,
            'last_batch_time': None,
            'average_batch_size': 0
        }
        
        # Start batch processor
        self._start_batch_processor()
    
    def _start_batch_processor(self):
        """Start the batch processor in background"""
        if not self.batch_processor_running:
            self.batch_processor_running = True
            thread = threading.Thread(target=self._batch_processor_loop, daemon=True)
            thread.start()
            logger.info("Message logging batch processor started")
    
    def _batch_processor_loop(self):
        """Main batch processor loop"""
        while self.batch_processor_running:
            try:
                current_time = time.time()
                should_process = False
                
                with self.buffer_lock:
                    buffer_size = len(self.message_buffer)
                    time_since_last_batch = current_time - self.last_batch_time
                    
                    # Determine if we should process batch
                    if buffer_size >= self.batch_size:
                        should_process = True
                        logger.debug(f"Processing batch due to size: {buffer_size}")
                    elif buffer_size > 0 and time_since_last_batch >= self.batch_timeout:
                        should_process = True
                        logger.debug(f"Processing batch due to timeout: {time_since_last_batch}s")
                    elif buffer_size >= self.memory_threshold:
                        should_process = True
                        self.stats['buffer_overflows'] += 1
                        logger.warning(f"Processing batch due to memory overflow: {buffer_size}")
                
                if should_process:
                    self._process_batch()
                
                # Sleep for a short interval
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Batch processor error: {e}")
                time.sleep(5)  # Wait longer on error
    
    def _process_batch(self):
        """Process a batch of messages"""
        try:
            batch_messages = []
            
            with self.buffer_lock:
                # Extract messages for processing
                while self.message_buffer and len(batch_messages) < self.batch_size:
                    batch_messages.append(self.message_buffer.popleft())
                
                self.last_batch_time = time.time()
            
            if not batch_messages:
                return
            
            # Process the batch
            self._write_batch_to_database(batch_messages)
            
            # Update statistics
            self.stats['batches_processed'] += 1
            self.stats['last_batch_time'] = datetime.now().isoformat()
            
            # Update average batch size
            total_messages = self.stats['messages_logged']
            self.stats['average_batch_size'] = total_messages / max(self.stats['batches_processed'], 1)
            
            logger.debug(f"Processed batch of {len(batch_messages)} messages")
            
        except Exception as e:
            logger.error(f"Batch processing error: {e}")
            # Put messages back in buffer on error
            with self.buffer_lock:
                for message in reversed(batch_messages):
                    self.message_buffer.appendleft(message)
    
    def _write_batch_to_database(self, messages: List[MessageLogEntry]):
        """Write batch of messages to database"""
        try:
            with self.db.get_cursor() as cursor:
                # Prepare batch insert
                insert_data = []
                for message in messages:
                    log_id = secrets.token_urlsafe(16)
                    insert_data.append((
                        log_id,
                        message.username,
                        message.email,
                        message.model,
                        json.dumps(message.messages),
                        message.research_model,
                        message.timestamp.isoformat(),
                        message.tokens_used,
                        message.processing_time_ms
                    ))
                
                # Batch insert
                cursor.executemany("""
                    INSERT INTO message_logs (
                        log_id, username, email, model, messages, research_model, 
                        time, tokens_used, processing_time_ms
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, insert_data)
                
                self.stats['messages_logged'] += len(messages)
                logger.debug(f"Successfully wrote {len(messages)} messages to database")
                
        except Exception as e:
            logger.error(f"Database batch write error: {e}")
            raise
    
    async def log_message(self, username: str, email: str, model: str, 
                         messages: List[Dict[str, Any]], research_model: bool = False,
                         tokens_used: int = 0, processing_time_ms: int = 0) -> bool:
        """Log a message (high-speed, non-blocking)"""
        try:
            # Create log entry
            log_entry = MessageLogEntry(
                username=username,
                email=email,
                model=model,
                messages=messages,
                research_model=research_model,
                tokens_used=tokens_used,
                processing_time_ms=processing_time_ms,
                timestamp=datetime.now()
            )
            
            # Add to buffer
            with self.buffer_lock:
                self.message_buffer.append(log_entry)
                
                # Check if buffer is getting too large
                if len(self.message_buffer) >= self.max_buffer_size:
                    logger.warning(f"Message buffer at maximum capacity: {self.max_buffer_size}")
                    # Force immediate processing
                    asyncio.create_task(self._force_batch_processing())
            
            return True
            
        except Exception as e:
            logger.error(f"Message logging error: {e}")
            return False
    
    async def _force_batch_processing(self):
        """Force immediate batch processing"""
        try:
            self._process_batch()
        except Exception as e:
            logger.error(f"Force batch processing error: {e}")
    
    async def log_batch_messages(self, batch_logs: List[BatchMessageLog]) -> bool:
        """Log multiple messages in batch"""
        try:
            for log in batch_logs:
                await self.log_message(
                    username=log.username,
                    email=log.email,
                    model=log.model,
                    messages=log.messages,
                    research_model=log.research_model,
                    tokens_used=log.tokens_used,
                    processing_time_ms=log.processing_time_ms
                )
            
            return True
            
        except Exception as e:
            logger.error(f"Batch message logging error: {e}")
            return False
    
    def get_user_message_logs(self, username: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """Get user message logs"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT log_id, model, research_model, time, tokens_used, processing_time_ms
                    FROM message_logs 
                    WHERE username = ?
                    ORDER BY time DESC 
                    LIMIT ? OFFSET ?
                """, (username, limit, offset))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting user message logs: {e}")
            return []
    
    def get_message_log_details(self, log_id: str, username: str) -> Optional[Dict[str, Any]]:
        """Get detailed message log (only for the user who created it)"""
        try:
            with self.db.get_cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM message_logs 
                    WHERE log_id = ? AND username = ?
                """, (log_id, username))
                
                row = cursor.fetchone()
                if row:
                    log_data = dict(row)
                    log_data['messages'] = json.loads(log_data['messages'])
                    return log_data
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting message log details: {e}")
            return None
    
    def get_system_message_stats(self) -> Dict[str, Any]:
        """Get system-wide message statistics"""
        try:
            with self.db.get_cursor() as cursor:
                # Total messages
                cursor.execute("SELECT COUNT(*) FROM message_logs")
                total_messages = cursor.fetchone()[0]
                
                # Messages today
                today = datetime.now().date().isoformat()
                cursor.execute("SELECT COUNT(*) FROM message_logs WHERE date(time) = ?", (today,))
                messages_today = cursor.fetchone()[0]
                
                # Messages this week
                week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
                cursor.execute("SELECT COUNT(*) FROM message_logs WHERE date(time) >= ?", (week_ago,))
                messages_this_week = cursor.fetchone()[0]
                
                # Top models
                cursor.execute("""
                    SELECT model, COUNT(*) as count 
                    FROM message_logs 
                    GROUP BY model 
                    ORDER BY count DESC 
                    LIMIT 10
                """)
                top_models = [{"model": row[0], "count": row[1]} for row in cursor.fetchall()]
                
                # Average tokens per message
                cursor.execute("SELECT AVG(tokens_used) FROM message_logs WHERE tokens_used > 0")
                avg_tokens = cursor.fetchone()[0] or 0
                
                # Average processing time
                cursor.execute("SELECT AVG(processing_time_ms) FROM message_logs WHERE processing_time_ms > 0")
                avg_processing_time = cursor.fetchone()[0] or 0
                
                return {
                    'total_messages': total_messages,
                    'messages_today': messages_today,
                    'messages_this_week': messages_this_week,
                    'top_models': top_models,
                    'average_tokens_per_message': round(avg_tokens, 2),
                    'average_processing_time_ms': round(avg_processing_time, 2),
                    'batch_processor_stats': self.stats
                }
                
        except Exception as e:
            logger.error(f"Error getting message stats: {e}")
            return {}
    
    def flush_buffer(self):
        """Manually flush the message buffer"""
        try:
            if self.message_buffer:
                logger.info(f"Manually flushing buffer with {len(self.message_buffer)} messages")
                self._process_batch()
                
        except Exception as e:
            logger.error(f"Buffer flush error: {e}")
    
    def get_buffer_status(self) -> Dict[str, Any]:
        """Get current buffer status"""
        with self.buffer_lock:
            return {
                'buffer_size': len(self.message_buffer),
                'max_buffer_size': self.max_buffer_size,
                'batch_size': self.batch_size,
                'batch_timeout': self.batch_timeout,
                'time_since_last_batch': time.time() - self.last_batch_time,
                'processor_running': self.batch_processor_running,
                'stats': self.stats
            }
    
    def shutdown(self):
        """Shutdown the logging service and flush remaining messages"""
        logger.info("Shutting down message logging service...")
        
        # Stop the batch processor
        self.batch_processor_running = False
        
        # Flush remaining messages
        self.flush_buffer()
        
        logger.info("Message logging service shutdown complete")
    
    def __del__(self):
        """Destructor to ensure clean shutdown"""
        try:
            self.shutdown()
        except:
            pass


# Global message logging service instance
message_logging_service = MessageLoggingService()


# Automatic daily limit reset task
class DailyLimitResetService:
    """Service to reset daily conversation limits"""
    
    def __init__(self):
        self.db = db_manager
        self.last_reset_date = datetime.now().date()
        self._start_reset_scheduler()
    
    def _start_reset_scheduler(self):
        """Start the daily reset scheduler"""
        thread = threading.Thread(target=self._reset_scheduler_loop, daemon=True)
        thread.start()
        logger.info("Daily limit reset scheduler started")
    
    def _reset_scheduler_loop(self):
        """Main reset scheduler loop"""
        while True:
            try:
                current_date = datetime.now().date()
                
                # Check if we need to reset (new day)
                if current_date > self.last_reset_date:
                    logger.info("Starting daily limit reset...")
                    updated_count = self.db.reset_daily_limits()
                    self.last_reset_date = current_date
                    logger.info(f"Daily limit reset complete. Updated {updated_count} users.")
                
                # Sleep for 1 hour before next check
                time.sleep(3600)
                
            except Exception as e:
                logger.error(f"Daily reset scheduler error: {e}")
                time.sleep(3600)  # Continue trying


# Global daily reset service instance
daily_reset_service = DailyLimitResetService()