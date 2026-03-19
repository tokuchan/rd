"""Tests for the SQLite block-cache adaptor."""

import pytest

from rd.adaptors.sqliteBlockCache import SqliteBlockCache
from rd.BlockCache.models import BLOCK_SIZE, Block, Key


@pytest.fixture()
def cache(tmp_path):
    """Return a fresh SqliteBlockCache backed by a temp file."""
    return SqliteBlockCache(f"sqlite:///{tmp_path}/test.db")


# ---------------------------------------------------------------------------
# store / get
# ---------------------------------------------------------------------------


def test_store_and_get(cache):
    key = Key(value="abc")
    block = Block(data=b"hello")
    stored = cache.store(key, block)
    assert stored.data == b"hello"

    retrieved = cache.get(key)
    assert retrieved is not None
    assert retrieved.data == b"hello"


def test_get_missing_returns_none(cache):
    assert cache.get(Key(value="no-such-key")) is None


def test_store_overwrites_existing(cache):
    key = Key(value="dup")
    cache.store(key, Block(data=b"first"))
    cache.store(key, Block(data=b"second"))
    result = cache.get(key)
    assert result is not None
    assert result.data == b"second"


def test_store_padded_block(cache):
    key = Key(value="padded")
    padded = Block(data=b"hi").pad(BLOCK_SIZE)
    stored = cache.store(key, padded)
    assert len(stored.data) == BLOCK_SIZE
    retrieved = cache.get(key)
    assert retrieved is not None
    assert len(retrieved.data) == BLOCK_SIZE
    assert retrieved.data[:2] == b"hi"


def test_store_returns_block(cache):
    key = Key(value="ret")
    block = Block(data=b"data")
    result = cache.store(key, block)
    assert isinstance(result, Block)
    assert result.data == b"data"


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


def test_delete_existing(cache):
    key = Key(value="del")
    cache.store(key, Block(data=b"to delete"))
    assert cache.delete(key) is True
    assert cache.get(key) is None


def test_delete_missing_returns_false(cache):
    assert cache.delete(Key(value="ghost")) is False


def test_delete_then_reinsert(cache):
    key = Key(value="cycle")
    cache.store(key, Block(data=b"v1"))
    cache.delete(key)
    cache.store(key, Block(data=b"v2"))
    result = cache.get(key)
    assert result is not None
    assert result.data == b"v2"


# ---------------------------------------------------------------------------
# In-memory (":memory:") variant
# ---------------------------------------------------------------------------


def test_in_memory_store_get():
    mem_cache = SqliteBlockCache("sqlite:///:memory:")
    key = Key(value="mem")
    mem_cache.store(key, Block(data=b"in memory"))
    result = mem_cache.get(key)
    assert result is not None
    assert result.data == b"in memory"
