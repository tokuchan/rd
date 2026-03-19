"""SQLAlchemy engine and session factory for the ReliableData store."""

import logging
import os
from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from rd.models import Base

logger = logging.getLogger(__name__)

DbUrl = os.environ.get("RD_DATABASE_URL", "sqlite:///./rd.db")

engine = create_engine(
    DbUrl,
    connect_args={"check_same_thread": False},  # required for SQLite
)


@event.listens_for(engine, "connect")
def _enableWal(dbapiConnection, connectionRecord) -> None:
    """Enable Write-Ahead Logging for safer concurrent access."""
    logger.debug("Enabling WAL journal mode on new connection")
    dbapiConnection.execute("PRAGMA journal_mode=WAL")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def initDb() -> None:
    """Create all tables defined in the schema."""
    logger.info("Initialising database schema at %s", DbUrl)
    Base.metadata.create_all(bind=engine)
    logger.debug("Database schema ready")


def getDb() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    logger.debug("Opening database session")
    db = SessionLocal()
    try:
        yield db
        logger.debug("Database session committed")
    finally:
        db.close()
        logger.debug("Database session closed")
