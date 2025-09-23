"""
Credit reset service for daily credit management
"""
import asyncio
from datetime import datetime, time, timedelta
from typing import Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.database.database import get_db_session
from app.database.models import User
from app.config.settings import get_settings
from app.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class CreditResetService:
    """Service for managing daily credit resets"""
    
    def __init__(self):
        self.reset_hour = settings.daily_usage_reset_hour
        self.is_running = False
        self._task = None
    
    async def start(self):
        """Start the credit reset service"""
        if self.is_running:
            return
        
        self.is_running = True
        self._task = asyncio.create_task(self._reset_worker())
        logger.info("Credit reset service started")
    
    async def stop(self):
        """Stop the credit reset service"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        
        logger.info("Credit reset service stopped")
    
    async def _reset_worker(self):
        """Background worker for credit resets"""
        while self.is_running:
            try:
                # Calculate next reset time
                now = datetime.now()
                next_reset = self._get_next_reset_time(now)
                
                # Wait until next reset time
                wait_seconds = (next_reset - now).total_seconds()
                logger.info(f"Next credit reset scheduled for {next_reset} (in {wait_seconds:.0f} seconds)")
                
                await asyncio.sleep(wait_seconds)
                
                if self.is_running:
                    await self._perform_credit_reset()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in credit reset worker: {e}")
                # Wait 1 hour before retrying on error
                await asyncio.sleep(3600)
    
    def _get_next_reset_time(self, current_time: datetime) -> datetime:
        """Calculate the next reset time"""
        today_reset = current_time.replace(
            hour=self.reset_hour,
            minute=0,
            second=0,
            microsecond=0
        )
        
        if current_time >= today_reset:
            # Reset time has passed today, schedule for tomorrow
            return today_reset + timedelta(days=1)
        else:
            # Reset time hasn't passed today
            return today_reset
    
    async def _perform_credit_reset(self):
        """Perform the daily credit reset for all users"""
        try:
            async with get_db_session() as session:
                # Get all active users
                result = await session.execute(
                    select(User).where(User.is_active == True)
                )
                users = result.scalars().all()
                
                reset_count = 0
                
                for user in users:
                    try:
                        # Get current limits
                        limits = user.limits or {}
                        reset_amount = limits.get("reset", 0)
                        
                        if reset_amount > 0:
                            # Reset conversation_limit to reset amount
                            limits["conversation_limit"] = reset_amount
                            user.limits = limits
                            reset_count += 1
                    
                    except Exception as e:
                        logger.error(f"Failed to reset credits for user {user.username}: {e}")
                        continue
                
                # Commit all changes
                await session.commit()
                
                logger.info(f"Credit reset completed for {reset_count} users")
                
                return {
                    "success": True,
                    "reset_count": reset_count,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            logger.error(f"Credit reset failed: {e}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def manual_credit_reset(self) -> Dict[str, Any]:
        """Manually trigger credit reset (for admin use)"""
        logger.info("Manual credit reset triggered")
        return await self._perform_credit_reset()
    
    async def reset_user_credits(self, user_id: int) -> Dict[str, Any]:
        """Reset credits for a specific user"""
        try:
            async with get_db_session() as session:
                result = await session.execute(
                    select(User).where(User.id == user_id)
                )
                user = result.scalar_one_or_none()
                
                if not user:
                    return {
                        "success": False,
                        "error": "User not found"
                    }
                
                # Get current limits
                limits = user.limits or {}
                reset_amount = limits.get("reset", 0)
                
                if reset_amount > 0:
                    # Reset conversation_limit to reset amount
                    limits["conversation_limit"] = reset_amount
                    user.limits = limits
                    
                    await session.commit()
                    
                    logger.info(f"Credits reset for user {user.username}")
                    
                    return {
                        "success": True,
                        "user_id": user_id,
                        "username": user.username,
                        "new_credits": reset_amount,
                        "timestamp": datetime.now().isoformat()
                    }
                else:
                    return {
                        "success": False,
                        "error": "User has no reset credits configured"
                    }
                
        except Exception as e:
            logger.error(f"Failed to reset credits for user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get current service status"""
        now = datetime.now()
        next_reset = self._get_next_reset_time(now)
        
        return {
            "is_running": self.is_running,
            "reset_hour": self.reset_hour,
            "current_time": now.isoformat(),
            "next_reset_time": next_reset.isoformat(),
            "time_until_reset": str(next_reset - now)
        }


# Global service instance
credit_reset_service = CreditResetService()