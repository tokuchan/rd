"""SQLite block-cache adaptor.

Stores blocks in a single SQLite table via SQLAlchemy.  The table is created
automatically on first use.
"""

from __future__ import annotations

import logging

from sqlalchemy import Column, LargeBinary, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Session

from rd.BlockCache.models import Block, Key

logger = logging.getLogger(__name__)


class _Base(DeclarativeBase):
    pass


class _BlockStore(_Base):
    """Internal SQLAlchemy ORM model for the block-cache table."""

    __tablename__ = "block_cache"

    key: str = Column(String, primary_key=True, index=True, nullable=False)
    data: bytes = Column(LargeBinary, nullable=False, default=b"")


class SqliteBlockCache:
    """Block-cache adaptor backed by a SQLite database.

    The database and table are created automatically when this object is
    instantiated, so no separate schema-migration step is required.

    :param db_url: SQLAlchemy database URL, e.g. ``"sqlite:///./rd.db"`` or
                   ``"sqlite:///:memory:"``.
    """

    def __init__(self, db_url: str) -> None:
        logger.debug("SqliteBlockCache: connecting to %s", db_url)
        self._engine = create_engine(db_url, connect_args={"check_same_thread": False})
        _Base.metadata.create_all(bind=self._engine)

    # ------------------------------------------------------------------
    # BlockCachePort interface
    # ------------------------------------------------------------------

    def store(self, key: Key, block: Block) -> Block:
        """Persist *block* under *key* (insert or update) and return it.

        :param key:   Cache key.
        :param block: Block to store.
        :returns:     The stored block with data as retrieved from the DB.
        """
        with Session(self._engine) as session:
            entry = session.get(_BlockStore, key.value)
            if entry is None:
                entry = _BlockStore(key=key.value, data=block.data)
                session.add(entry)
            else:
                entry.data = block.data  # type: ignore[assignment]
            session.commit()
            session.refresh(entry)
            return Block(data=bytes(entry.data))

    def get(self, key: Key) -> Block | None:
        """Return the block stored under *key*, or ``None`` if absent.

        :param key: Cache key.
        :returns:   :class:`~rd.BlockCache.models.Block` or ``None``.
        """
        with Session(self._engine) as session:
            entry = session.get(_BlockStore, key.value)
            if entry is None:
                return None
            return Block(data=bytes(entry.data))

    def delete(self, key: Key) -> bool:
        """Delete the block stored under *key*.

        :param key: Cache key.
        :returns:   ``True`` if the block existed and was deleted, ``False``
                    if no block with that key was found.
        """
        with Session(self._engine) as session:
            entry = session.get(_BlockStore, key.value)
            if entry is None:
                return False
            session.delete(entry)
            session.commit()
            return True
