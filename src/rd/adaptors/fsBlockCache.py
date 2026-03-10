"""Filesystem block-cache adaptor.

Stores blocks as individual files inside a directory, with each file named
after its key (similar to git's loose-object store).  The directory is
created automatically when this adaptor is instantiated.

Key values are expected to be composed of characters that are valid in
filenames (e.g. hex strings).  Keys that contain path separators or other
unsafe characters are percent-encoded to avoid directory traversal.
"""

from __future__ import annotations

import logging
import urllib.parse
from pathlib import Path

from rd.BlockCache.models import Block, Key

logger = logging.getLogger(__name__)


def _safe_name(key: Key) -> str:
    """Return a filesystem-safe name derived from *key.value*.

    Characters that are not alphanumeric, hyphens, underscores, or dots are
    percent-encoded so that the resulting string is always a valid filename.
    """
    return urllib.parse.quote(key.value, safe="-_.")


class FsBlockCache:
    """Block-cache adaptor that stores each block as a file on the filesystem.

    :param directory: Path to the directory used as the store root.  Created
                      (including parents) if it does not already exist.
    """

    def __init__(self, directory: str) -> None:
        self._dir = Path(directory)
        self._dir.mkdir(parents=True, exist_ok=True)
        logger.debug("FsBlockCache: using directory %s", self._dir)

    # ------------------------------------------------------------------
    # BlockCachePort interface
    # ------------------------------------------------------------------

    def store(self, key: Key, block: Block) -> Block:
        """Write *block* to a file named after *key*.

        :param key:   Cache key.
        :param block: Block to store.
        :returns:     The stored block.
        """
        path = self._dir / _safe_name(key)
        path.write_bytes(block.data)
        return block

    def get(self, key: Key) -> Block | None:
        """Read and return the block stored under *key*, or ``None`` if absent.

        :param key: Cache key.
        :returns:   :class:`~rd.BlockCache.models.Block` or ``None``.
        """
        path = self._dir / _safe_name(key)
        if not path.exists():
            return None
        return Block(data=path.read_bytes())

    # ------------------------------------------------------------------
    # Extended operations (not part of the port protocol)
    # ------------------------------------------------------------------

    def delete(self, key: Key) -> bool:
        """Delete the file for *key*.

        :param key: Cache key.
        :returns:   ``True`` if the block existed and was deleted, ``False``
                    if no file with that key was found.
        """
        path = self._dir / _safe_name(key)
        if not path.exists():
            return False
        path.unlink()
        return True
