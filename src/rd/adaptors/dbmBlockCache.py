"""DBM block-cache adaptor.

Stores blocks in a DBM database file using Python's built-in :mod:`dbm` module.
DBM provides a simple persistent key→bytes store.  The exact backing format
(``gdbm``, ``ndbm``, ``dumbdbm``) depends on the platform; this adaptor is
agnostic to which variant is available.
"""

from __future__ import annotations

import dbm
import logging

from rd.BlockCache.models import Block, Key

logger = logging.getLogger(__name__)


class DbmBlockCache:
    """Block-cache adaptor backed by a DBM database file.

    :param path: Filesystem path for the DBM database (without extension;
                 DBM may append ``.db``, ``.dir``/``.pag``, etc.).
    """

    def __init__(self, path: str) -> None:
        logger.debug("DbmBlockCache: using database at %s", path)
        self._path = path
        # Touch the database so it is created immediately.
        with dbm.open(self._path, "c"):
            pass

    # ------------------------------------------------------------------
    # BlockCachePort interface
    # ------------------------------------------------------------------

    def store(self, key: Key, block: Block) -> Block:
        """Persist *block* under *key* and return it.

        :param key:   Cache key.
        :param block: Block to store.
        :returns:     The stored block.
        """
        with dbm.open(self._path, "c") as db:
            db[key.value] = block.data
        return block

    def get(self, key: Key) -> Block | None:
        """Return the block stored under *key*, or ``None`` if absent.

        :param key: Cache key.
        :returns:   :class:`~rd.BlockCache.models.Block` or ``None``.
        """
        with dbm.open(self._path, "r") as db:
            try:
                raw = db[key.value]
            except KeyError:
                return None
        return Block(data=bytes(raw))

    def delete(self, key: Key) -> bool:
        """Delete the block stored under *key*.

        :param key: Cache key.
        :returns:   ``True`` if the block existed and was deleted, ``False``
                    if no block with that key was found.
        """
        with dbm.open(self._path, "c") as db:
            if key.value not in db:
                return False
            del db[key.value]
            return True
