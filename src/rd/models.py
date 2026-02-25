"""Database schema for the ReliableData key/value store.

All schema is defined in the single ``Store`` class so that it is easy to
modify in one place.
"""

from sqlalchemy import Column, DateTime, LargeBinary, String, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Store(Base):
    """Block cache table.

    Modify this class to change the database schema.
    """

    __tablename__ = "store"

    block_id: str = Column(String, primary_key=True, index=True, nullable=False)
    block_data: bytes = Column(LargeBinary, nullable=False, default=b"")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
