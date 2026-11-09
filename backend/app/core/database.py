import asyncio
import socket
import time
from typing import AsyncGenerator, Dict, Any
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from app.core.config import settings

# Initialize Async SQLAlchemy Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    connect_args={"timeout": 10},
)

# Async Session Factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for providing database sessions per request."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


def _probe_tcp_port(host: str, port: int, timeout: float = 0.5) -> bool:
    """Synchronous socket probe with strict timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False


async def check_db_connectivity() -> Dict[str, Any]:
    """
    Safely ping the database to assess connection status and latency.
    Uses a fast socket probe to fail immediately if database is offline.
    """
    start_time = time.perf_counter()

    # Step 1: Fast TCP probe (0.5s max)
    is_open = await asyncio.to_thread(
        _probe_tcp_port, settings.POSTGRES_HOST, settings.POSTGRES_PORT, 0.5
    )
    if not is_open:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "connected": False,
            "latency_ms": latency_ms,
            "message": f"Database host {settings.POSTGRES_HOST}:{settings.POSTGRES_PORT} is unreachable or offline.",
            "error": "ConnectionRefusedOrTimedOut",
        }

    # Step 2: Database query verification
    try:
        async with engine.connect() as conn:
            result = await conn.execute(text("SELECT 1"))
            row = result.scalar()
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            if row == 1:
                return {
                    "connected": True,
                    "latency_ms": latency_ms,
                    "message": "Database is reachable and operational.",
                    "error": None,
                }
            return {
                "connected": False,
                "latency_ms": latency_ms,
                "message": "Unexpected ping response.",
                "error": "Query did not return 1",
            }
    except Exception as exc:
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
        return {
            "connected": False,
            "latency_ms": latency_ms,
            "message": "Database query failed.",
            "error": str(exc),
        }
