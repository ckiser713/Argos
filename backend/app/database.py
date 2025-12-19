"""
SQLAlchemy Database Configuration for Argos Backend.

This module provides the database engine, session management, and base model
for SQLAlchemy ORM. It supports both SQLite (local development) and PostgreSQL
(strix/production environments).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager, contextmanager
from typing import AsyncIterator, Iterator

from sqlalchemy import create_engine, event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import get_settings

logger = logging.getLogger(__name__)

# SQLAlchemy Base for ORM models
Base = declarative_base()

# Global engine and session factory references
_sync_engine = None
_async_engine = None
_sync_session_factory = None
_async_session_factory = None


def _get_sync_database_url() -> str:
    """Get the synchronous database URL based on environment."""
    settings = get_settings()
    url = settings.database_url
    
    # For PostgreSQL, ensure we use psycopg2 driver for sync operations
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg2://", 1)
    if url.startswith("postgresql+"):
        return url
    
    return url


def _get_async_database_url() -> str:
    """Get the asynchronous database URL based on environment."""
    settings = get_settings()
    url = settings.database_url
    
    # For PostgreSQL, use asyncpg driver for async operations
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+asyncpg://", 1)
    if url.startswith("postgresql+"):
        return url
    
    # SQLite async requires aiosqlite
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "sqlite+aiosqlite:///")
    
    return url


def get_sync_engine():
    """Get or create the synchronous SQLAlchemy engine."""
    global _sync_engine
    
    if _sync_engine is None:
        url = _get_sync_database_url()
        settings = get_settings()
        
        # SQLite-specific configuration
        if url.startswith("sqlite"):
            _sync_engine = create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.debug,
            )
            # Enable WAL mode for SQLite
            @event.listens_for(_sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        else:
            # PostgreSQL configuration
            _sync_engine = create_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=settings.debug,
            )
        
        logger.info(f"Created sync database engine: {url.split('@')[-1] if '@' in url else url}")
    
    return _sync_engine


def get_async_engine():
    """Get or create the asynchronous SQLAlchemy engine."""
    global _async_engine
    
    if _async_engine is None:
        url = _get_async_database_url()
        settings = get_settings()
        
        # SQLite-specific configuration
        if url.startswith("sqlite"):
            _async_engine = create_async_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=settings.debug,
            )
        else:
            # PostgreSQL configuration
            _async_engine = create_async_engine(
                url,
                pool_size=5,
                max_overflow=10,
                pool_pre_ping=True,
                pool_recycle=300,
                echo=settings.debug,
            )
        
        logger.info(f"Created async database engine: {url.split('@')[-1] if '@' in url else url}")
    
    return _async_engine


def get_sync_session_factory() -> sessionmaker:
    """Get or create the synchronous session factory."""
    global _sync_session_factory
    
    if _sync_session_factory is None:
        engine = get_sync_engine()
        _sync_session_factory = sessionmaker(
            bind=engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    
    return _sync_session_factory


def get_async_session_factory() -> async_sessionmaker:
    """Get or create the asynchronous session factory."""
    global _async_session_factory
    
    if _async_session_factory is None:
        engine = get_async_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    
    return _async_session_factory


@contextmanager
def get_db_session() -> Iterator[Session]:
    """
    Context manager for synchronous database sessions.
    
    Usage:
        with get_db_session() as session:
            result = session.execute(text("SELECT 1"))
    """
    session_factory = get_sync_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_db_session() -> AsyncIterator[AsyncSession]:
    """
    Async context manager for asynchronous database sessions.
    
    Usage:
        async with get_async_db_session() as session:
            result = await session.execute(text("SELECT 1"))
    """
    session_factory = get_async_session_factory()
    session = session_factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


async def get_db() -> AsyncIterator[AsyncSession]:
    """
    FastAPI dependency for async database sessions.
    
    Usage:
        @router.get("/items")
        async def get_items(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with get_async_db_session() as session:
        yield session


def init_database() -> None:
    """
    Initialize the database by creating all tables.
    
    For production, use Alembic migrations instead.
    This is mainly for local development and testing.
    """
    engine = get_sync_engine()
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")


async def async_init_database() -> None:
    """
    Asynchronously initialize the database by creating all tables.
    """
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully (async)")


def check_database_connection() -> bool:
    """
    Check if the database connection is working.
    
    Returns:
        True if connection successful, False otherwise.
    """
    try:
        engine = get_sync_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


async def async_check_database_connection() -> bool:
    """
    Asynchronously check if the database connection is working.
    
    Returns:
        True if connection successful, False otherwise.
    """
    try:
        engine = get_async_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.error(f"Database connection check failed: {e}")
        return False


def close_database_connections() -> None:
    """Close all database connections and dispose of engines."""
    global _sync_engine, _async_engine, _sync_session_factory, _async_session_factory
    
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
        _sync_session_factory = None
        logger.info("Closed sync database engine")
    
    if _async_engine is not None:
        # Note: For async engine, should be called within async context
        # This is a sync fallback
        _async_engine = None
        _async_session_factory = None
        logger.info("Closed async database engine reference")


async def async_close_database_connections() -> None:
    """Asynchronously close all database connections and dispose of engines."""
    global _sync_engine, _async_engine, _sync_session_factory, _async_session_factory
    
    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None
        _async_session_factory = None
        logger.info("Closed async database engine")
    
    if _sync_engine is not None:
        _sync_engine.dispose()
        _sync_engine = None
        _sync_session_factory = None
        logger.info("Closed sync database engine")
