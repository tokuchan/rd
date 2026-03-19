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

    blockId: str = Column("block_id", String, primary_key=True, index=True, nullable=False)
    blockData: bytes = Column("block_data", LargeBinary, nullable=False, default=b"")
    createdAt = Column(
        "created_at", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updatedAt = Column(
        "updated_at",
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
