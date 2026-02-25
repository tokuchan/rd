"""Database schema for the ReliableData key/value store.

All schema is defined in the single ``Store`` class so that it is easy to
modify in one place.
"""

from sqlalchemy import Column, DateTime, String, func
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class Store(Base):
    """Key/value store table.

    Modify this class to change the database schema.
    """

    __tablename__ = "store"

    key: str = Column(String, primary_key=True, index=True, nullable=False)
    value: str = Column(String, nullable=False, default="")
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
