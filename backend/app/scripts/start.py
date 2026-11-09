"""
Resilient production entrypoint script for VyapaarSetu.
1. Checks database connectivity.
2. Applies Alembic migrations and seeds demo data if database is reachable.
3. If database is unreachable, prints an informative warning and continues to launch Uvicorn.
4. Starts Uvicorn ASGI server on $PORT (defaults to 8000).
"""
import os
import sys
import socket
import logging
import subprocess
from urllib.parse import urlparse

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("startup")


def is_database_reachable(host: str, port: int, timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, OSError):
        return False


def main():
    port = int(os.environ.get("PORT", "8000"))

    # Import settings to trigger URL normalization
    from app.core.config import settings

    logger.info("Initializing VyapaarSetu (environment=%s, port=%d)...", settings.ENVIRONMENT, port)

    # Parse target database connection
    parsed = urlparse(settings.DATABASE_URL)
    db_host = parsed.hostname or settings.POSTGRES_HOST or "127.0.0.1"
    db_port = parsed.port or settings.POSTGRES_PORT or 5432

    logger.info("Probing database at %s:%s...", db_host, db_port)
    db_online = is_database_reachable(db_host, db_port, timeout=2.0)

    if db_online:
        logger.info("[STARTUP] Database connection established at %s:%s.", db_host, db_port)
        logger.info("[STARTUP] Applying Alembic database migrations to head...")
        try:
            res = subprocess.run(
                ["alembic", "upgrade", "head"],
                capture_output=True,
                text=True,
                timeout=25,
            )
            if res.returncode == 0:
                logger.info("[STARTUP] Migrations applied successfully.")
                if res.stdout.strip():
                    logger.info("[STARTUP] Alembic output:\n%s", res.stdout.strip())
            else:
                logger.error(
                    "[STARTUP ERROR] Alembic migration failed (exit code %d).\nSTDERR: %s\nSTDOUT: %s",
                    res.returncode,
                    res.stderr.strip(),
                    res.stdout.strip(),
                )
        except subprocess.TimeoutExpired:
            logger.error("[STARTUP ERROR] Alembic migration timed out after 25s. Continuing to start web server...")
        except Exception as exc:
            logger.error("[STARTUP ERROR] Alembic migration encountered error: %s. Continuing startup...", exc)

        logger.info("[STARTUP] Checking demo data seeder...")
        try:
            res = subprocess.run(
                [sys.executable, "-m", "app.seeds.demo_data"],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if res.returncode == 0:
                logger.info("[STARTUP] Demo data checked/seeded successfully.")
            else:
                logger.warning(
                    "[STARTUP WARNING] Seed returned non-zero (%d): %s",
                    res.returncode,
                    res.stderr.strip() or res.stdout.strip(),
                )
        except subprocess.TimeoutExpired:
            logger.warning("[STARTUP WARNING] Demo data seeder timed out after 15s. Continuing startup...")
        except Exception as exc:
            logger.warning("[STARTUP WARNING] Seed script skipped: %s", exc)
    else:
        logger.warning(
            "\n"
            "================================================================================\n"
            "[STARTUP WARNING] Database connection refused at %s:%s!\n"
            "The backend will start in degraded mode.\n"
            "\n"
            "If deploying on Render, please configure a PostgreSQL database (e.g., Neon or Render PostgreSQL)\n"
            "and set the 'DATABASE_URL' environment variable in your Render Dashboard:\n"
            "DATABASE_URL=postgresql+asyncpg://<user>:<password>@<host>/<database>?ssl=require\n"
            "================================================================================\n",
            db_host,
            db_port,
        )

    # Launch Uvicorn
    logger.info("Starting Uvicorn ASGI server on 0.0.0.0:%d...", port)
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, log_level="info")


if __name__ == "__main__":
    main()
