"""SQLAlchemy engine and session factory for the ReliableData store."""

import logging
import os
from collections.abc import Generator

from sqlalchemy import event, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from rd.models import Base

logger = logging.getLogger(__name__)

_DB_URL = os.environ.get("RD_DATABASE_URL", "sqlite:///./rd.db")

engine = create_engine(
    _DB_URL,
    connect_args={"check_same_thread": False},  # required for SQLite
)


@event.listens_for(engine, "connect")
def _enable_wal(dbapi_connection, connection_record) -> None:
    """Enable Write-Ahead Logging for safer concurrent access."""
    logger.debug("Enabling WAL journal mode on new connection")
    dbapi_connection.execute("PRAGMA journal_mode=WAL")


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db() -> None:
    """Create all tables defined in the schema."""
    logger.info("Initialising database schema at %s", _DB_URL)
    Base.metadata.create_all(bind=engine)
    logger.debug("Database schema ready")


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency that yields a database session."""
    logger.debug("Opening database session")
    db = SessionLocal()
    try:
        yield db
        logger.debug("Database session committed")
    finally:
        db.close()
        logger.debug("Database session closed")
