"""BlockCache port – defines how callers interact with any block-cache back-end.

Any class that implements both :meth:`store` and :meth:`get` with the correct
signatures satisfies this protocol and can be used wherever a
:class:`BlockCachePort` is expected.
"""

from __future__ import annotations

from typing import Protocol

from rd.BlockCache.models import Block, Key


class BlockCachePort(Protocol):
    """Protocol that all block-cache adaptors must satisfy.

    Two operations are required:

    * :meth:`store` — persist a block under a key and return the stored block.
    * :meth:`get`   — retrieve a block by key, or ``None`` if absent.
    """

    def store(self, key: Key, block: Block) -> Block:
        """Persist *block* under *key* and return the stored block.

        :param key:   The key under which the block is stored.
        :param block: The block to store.
        :returns:     The stored block (may differ from the input if the
                      adaptor transforms the data, e.g. compression).
        """
        ...  # pragma: no cover

    def get(self, key: Key) -> Block | None:
        """Return the block stored under *key*, or ``None`` if absent.

        :param key: The key to look up.
        :returns:   The stored :class:`Block`, or ``None``.
        """
        ...  # pragma: no cover
