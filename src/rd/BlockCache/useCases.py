"""Use-case logic for the BlockCache.

This module contains the pure application logic that sits above the block-cache
port.  It is responsible for:

* Deriving deterministic block keys from a data-context key pair and a path
  (file-addressed blocks).
* Deriving content-addressed block keys (data blocks).
* Storing and retrieving blocks through any :class:`~rd.BlockCache.ports.BlockCachePort`
  adaptor.

Nothing in this module imports from a specific adaptor — only from the domain
model (``models``, ``errors``) and the port (``ports``).
"""

from __future__ import annotations

from typing import Union

from Crypto.Hash import SHA3_256

from rd.BlockCache.errors import BlockTooLargeError
from rd.BlockCache.models import BLOCK_SIZE, Block, Key
from rd.BlockCache.ports import BlockCachePort

# ---------------------------------------------------------------------------
# Key derivation
# ---------------------------------------------------------------------------


def derive_file_block_key(context_key: str, path: Union[str, int]) -> Key:
    """Derive a deterministic block key from a data-context key and a path.

    The key is ``SHA3-256(bytes.fromhex(context_key) ‖ str(path).encode())``.

    :param context_key: Hex-encoded public context key (e.g. ED25519 public key).
    :param path:        Path string or integer block index.
    :returns:           A :class:`~rd.BlockCache.models.Key` whose value is the
                        hex-encoded SHA3-256 digest.
    :raises ValueError: If *context_key* is not valid hex.
    """
    try:
        context_key_bytes = bytes.fromhex(context_key)
    except ValueError:
        raise ValueError("contextKey must be a valid hex-encoded public key")

    h = SHA3_256.new()
    h.update(context_key_bytes)
    h.update(str(path).encode())
    return Key(value=h.hexdigest())


def derive_data_block_key(block: Block) -> Key:
    """Derive a content-addressed key as ``SHA3-256(block.data)``.

    :param block: The block whose content is hashed.
    :returns:     A :class:`~rd.BlockCache.models.Key` whose value is the
                  hex-encoded SHA3-256 digest.
    """
    h = SHA3_256.new()
    h.update(block.data)
    return Key(value=h.hexdigest())


# ---------------------------------------------------------------------------
# Store helpers
# ---------------------------------------------------------------------------


def store_file_block(
    cache: BlockCachePort,
    context_key: str,
    path: Union[str, int],
    data: bytes,
    block_size: int = BLOCK_SIZE,
) -> tuple[Key, Block]:
    """Pad *data* to *block_size*, derive a file-addressed key, and store the block.

    :param cache:       A :class:`~rd.BlockCache.ports.BlockCachePort` adaptor.
    :param context_key: Hex-encoded public context key.
    :param path:        Path string or integer block index.
    :param data:        Raw bytes to store (must not exceed *block_size*).
    :param block_size:  Target block size in bytes (default: :data:`BLOCK_SIZE`).
    :returns:           A ``(key, block)`` tuple of the derived key and stored block.
    :raises BlockTooLargeError: If ``len(data) > block_size``.
    :raises ValueError:         If *context_key* is not valid hex.
    """
    if len(data) > block_size:
        raise BlockTooLargeError(
            f"Data ({len(data)} bytes) exceeds block_size ({block_size} bytes)"
        )
    key = derive_file_block_key(context_key, path)
    block = Block(data=data).pad(block_size)
    stored = cache.store(key, block)
    return key, stored


def store_data_block(
    cache: BlockCachePort,
    data: bytes,
    block_size: int = BLOCK_SIZE,
) -> tuple[Key, Block]:
    """Pad *data* to *block_size*, derive a content-addressed key, and store the block.

    :param cache:      A :class:`~rd.BlockCache.ports.BlockCachePort` adaptor.
    :param data:       Raw bytes to store (must not exceed *block_size*).
    :param block_size: Target block size in bytes (default: :data:`BLOCK_SIZE`).
    :returns:          A ``(key, block)`` tuple of the derived key and stored block.
    :raises BlockTooLargeError: If ``len(data) > block_size``.
    """
    if len(data) > block_size:
        raise BlockTooLargeError(
            f"Data ({len(data)} bytes) exceeds block_size ({block_size} bytes)"
        )
    block = Block(data=data).pad(block_size)
    key = derive_data_block_key(block)
    stored = cache.store(key, block)
    return key, stored
