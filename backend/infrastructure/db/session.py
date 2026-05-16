"""Database engine and session factory."""

from __future__ import annotations

import logging
import time
from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from backend.config import settings
from backend.infrastructure.db.models import Base

logger = logging.getLogger(__name__)

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    future=True,
)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def wait_for_database(max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    """Block until PostgreSQL accepts connections (Docker startup)."""
    for attempt in range(1, max_attempts + 1):
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("Database connection established")
            return
        except Exception as exc:
            if attempt == max_attempts:
                raise RuntimeError("Could not connect to database") from exc
            logger.warning("Database not ready (attempt %d/%d): %s", attempt, max_attempts, exc)
            time.sleep(delay_seconds)


def init_database() -> None:
    wait_for_database()
    Base.metadata.create_all(bind=engine)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
