from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from typing import AsyncGenerator
from app.core.config import settings

# Create async PostgreSQL engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,  # Log SQL queries in debug mode
    future=True,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=10,  # Connection pool size
    max_overflow=20,  # Max connections beyond pool_size
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for ORM models
Base = declarative_base()


# Dependency to get async database session
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Async database session dependency.
    Yields an async database session and ensures it's closed after use.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Function to initialize database
async def init_db():
    """
    Initialize database by creating all tables.
    Call this at application startup.
    Note: In production, use Alembic migrations instead.
    """
    async with engine.begin() as conn:
        # Import all models to register them
        from app.models import user  # noqa: F401
        
        # Create tables (only for development)
        # In production, use: alembic upgrade head
        # if settings.DEBUG:
        #     await conn.run_sync(Base.metadata.create_all)
        #     print("✅ Database tables created successfully!")


