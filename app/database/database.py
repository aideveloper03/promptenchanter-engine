"""
Database connection and session management
"""
import os
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from app.config.settings import get_settings

settings = get_settings()

# Database configuration
DATABASE_URL = getattr(settings, 'database_url', 'sqlite+aiosqlite:///./promptenchanter.db')

# For SQLite, ensure proper connection parameters
engine_kwargs = {
    "echo": settings.debug,
    "future": True,
    "pool_pre_ping": True,
}

# Add SQLite-specific configuration
if "sqlite" in DATABASE_URL:
    # SQLite connection arguments to handle permissions issues
    engine_kwargs["connect_args"] = {
        "check_same_thread": False,
        "timeout": 30,  # 30 second timeout for database locks
    }

# Create async engine
engine = create_async_engine(DATABASE_URL, **engine_kwargs)

# Create session factory
async_session_factory = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Get database session (for FastAPI dependency injection)"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_session_context() -> AsyncGenerator[AsyncSession, None]:
    """Get database session as async context manager"""
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database():
    """Initialize database tables"""
    from app.database.models import Base
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_database():
    """Close database connections"""
    await engine.dispose()