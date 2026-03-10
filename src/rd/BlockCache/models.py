"""Data types for the BlockCache domain.

``Key``  – an opaque string identifier for a block.
``Block`` – a fixed-size chunk of bytes stored in (and retrieved from) the cache.
"""

from __future__ import annotations

from dataclasses import dataclass

from rd.BlockCache.errors import BlockTooLargeError

# Default block size: 4 KiB (power of two).
BLOCK_SIZE: int = 4096


@dataclass(frozen=True)
class Key:
    """An opaque string key that identifies a block in the cache.

    In practice the value is a hex-encoded SHA3-256 digest, but the type
    makes no assumption about format — any string is valid.
    """

    value: str


@dataclass
class Block:
    """A chunk of raw bytes stored in the cache.

    Attributes:
        data: The raw bytes of the block.
    """

    data: bytes

    def pad(self, block_size: int = BLOCK_SIZE) -> "Block":
        """Return a new :class:`Block` padded to *block_size* bytes with ``\\x00``.

        :param block_size: Target size in bytes (default: :data:`BLOCK_SIZE`).
        :raises BlockTooLargeError: If ``len(self.data) > block_size``.
        """
        if len(self.data) > block_size:
            raise BlockTooLargeError(
                f"Block data ({len(self.data)} bytes) exceeds block_size ({block_size} bytes)"
            )
        padding = block_size - len(self.data)
        return Block(data=self.data + b"\x00" * padding)

    def __len__(self) -> int:
        return len(self.data)
