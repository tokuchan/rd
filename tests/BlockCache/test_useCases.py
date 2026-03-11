"""Tests for BlockCache use-case logic."""

import pytest
from Crypto.Hash import SHA3_256

from rd.BlockCache.errors import BlockTooLargeError
from rd.BlockCache.models import BLOCK_SIZE, Block, Key
from rd.BlockCache.useCases import (
    derive_data_block_key,
    derive_file_block_key,
    store_data_block,
    store_file_block,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _InMemoryCache:
    """Minimal in-memory BlockCachePort implementation for testing."""

    def __init__(self):
        self._store: dict[str, bytes] = {}

    def store(self, key: Key, block: Block) -> Block:
        self._store[key.value] = block.data
        return block

    def get(self, key: Key) -> Block | None:
        data = self._store.get(key.value)
        return Block(data=data) if data is not None else None

    def delete(self, key: Key) -> bool:
        if key.value not in self._store:
            return False
        del self._store[key.value]
        return True


# ---------------------------------------------------------------------------
# derive_file_block_key
# ---------------------------------------------------------------------------


def test_derive_file_block_key_string_path():
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    key = derive_file_block_key(context_key, "/readme.txt")

    h = SHA3_256.new()
    h.update(bytes.fromhex(context_key))
    h.update(b"/readme.txt")
    assert key.value == h.hexdigest()


def test_derive_file_block_key_integer_path():
    context_key = "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"
    key = derive_file_block_key(context_key, 42)

    h = SHA3_256.new()
    h.update(bytes.fromhex(context_key))
    h.update(b"42")
    assert key.value == h.hexdigest()


def test_derive_file_block_key_invalid_hex_raises():
    with pytest.raises(ValueError, match="contextKey must be a valid hex-encoded public key"):
        derive_file_block_key("not-valid-hex", "/path")


def test_derive_file_block_key_returns_key_type():
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    result = derive_file_block_key(context_key, "p")
    assert isinstance(result, Key)


def test_derive_file_block_key_deterministic():
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    k1 = derive_file_block_key(context_key, "/foo")
    k2 = derive_file_block_key(context_key, "/foo")
    assert k1 == k2


def test_derive_file_block_key_different_paths_differ():
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    k1 = derive_file_block_key(context_key, "/a")
    k2 = derive_file_block_key(context_key, "/b")
    assert k1 != k2


# ---------------------------------------------------------------------------
# derive_data_block_key
# ---------------------------------------------------------------------------


def test_derive_data_block_key():
    block = Block(data=b"hello\x00\x00\x00")
    key = derive_data_block_key(block)

    h = SHA3_256.new()
    h.update(b"hello\x00\x00\x00")
    assert key.value == h.hexdigest()


def test_derive_data_block_key_returns_key_type():
    key = derive_data_block_key(Block(data=b"x"))
    assert isinstance(key, Key)


def test_derive_data_block_key_deterministic():
    block = Block(data=b"deterministic data")
    k1 = derive_data_block_key(block)
    k2 = derive_data_block_key(block)
    assert k1 == k2


def test_derive_data_block_key_different_data_differ():
    k1 = derive_data_block_key(Block(data=b"a"))
    k2 = derive_data_block_key(Block(data=b"b"))
    assert k1 != k2


# ---------------------------------------------------------------------------
# store_file_block
# ---------------------------------------------------------------------------


def test_store_file_block_pads_and_stores():
    cache = _InMemoryCache()
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    key, block = store_file_block(cache, context_key, "/readme.txt", b"hello")

    assert len(block.data) == BLOCK_SIZE
    assert block.data[:5] == b"hello"
    assert block.data[5:] == b"\x00" * (BLOCK_SIZE - 5)
    # Key should match derive_file_block_key
    expected_key = derive_file_block_key(context_key, "/readme.txt")
    assert key == expected_key


def test_store_file_block_rejects_oversized():
    cache = _InMemoryCache()
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    with pytest.raises(BlockTooLargeError):
        store_file_block(cache, context_key, "/f", b"x" * (BLOCK_SIZE + 1))


def test_store_file_block_invalid_key_raises():
    cache = _InMemoryCache()
    with pytest.raises(ValueError):
        store_file_block(cache, "invalid-hex", "/f", b"data")


def test_store_file_block_custom_block_size():
    cache = _InMemoryCache()
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    key, block = store_file_block(cache, context_key, "/x", b"hi", block_size=8)
    assert len(block.data) == 8


# ---------------------------------------------------------------------------
# store_data_block
# ---------------------------------------------------------------------------


def test_store_data_block_pads_and_stores():
    cache = _InMemoryCache()
    key, block = store_data_block(cache, b"content addressed")

    assert len(block.data) == BLOCK_SIZE
    assert block.data[:17] == b"content addressed"
    # Key must match hash of the padded block
    expected_key = derive_data_block_key(block)
    assert key == expected_key


def test_store_data_block_rejects_oversized():
    cache = _InMemoryCache()
    with pytest.raises(BlockTooLargeError):
        store_data_block(cache, b"x" * (BLOCK_SIZE + 1))


def test_store_data_block_same_content_same_key():
    cache = _InMemoryCache()
    k1, _ = store_data_block(cache, b"dedup")
    k2, _ = store_data_block(cache, b"dedup")
    assert k1 == k2


def test_store_data_block_different_content_different_keys():
    cache = _InMemoryCache()
    k1, _ = store_data_block(cache, b"alpha")
    k2, _ = store_data_block(cache, b"beta")
    assert k1 != k2
