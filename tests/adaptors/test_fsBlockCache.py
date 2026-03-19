"""Tests for the filesystem block-cache adaptor."""

import pytest

from rd.adaptors.fsBlockCache import FsBlockCache, _safe_name
from rd.BlockCache.models import BLOCK_SIZE, Block, Key


@pytest.fixture()
def cache(tmp_path):
    """Return a fresh FsBlockCache backed by a temp directory."""
    return FsBlockCache(str(tmp_path / "fs_cache"))


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
# Directory auto-creation
# ---------------------------------------------------------------------------


def test_directory_created_automatically(tmp_path):
    nested = str(tmp_path / "a" / "b" / "c")
    c = FsBlockCache(nested)
    c.store(Key(value="x"), Block(data=b"y"))
    assert (tmp_path / "a" / "b" / "c").is_dir()


# ---------------------------------------------------------------------------
# Key safety (_safe_name)
# ---------------------------------------------------------------------------


def test_safe_name_hex_key_unchanged():
    key = Key(value="d75a980182b10ab7d54bfed3c964073a")
    assert _safe_name(key) == "d75a980182b10ab7d54bfed3c964073a"


def test_safe_name_encodes_slash():
    key = Key(value="path/with/slashes")
    name = _safe_name(key)
    assert "/" not in name


def test_safe_name_roundtrip_store_get(tmp_path):
    """Keys with special characters must still round-trip correctly."""
    c = FsBlockCache(str(tmp_path / "special"))
    key = Key(value="hello/world")
    c.store(key, Block(data=b"data"))
    result = c.get(key)
    assert result is not None
    assert result.data == b"data"


# ---------------------------------------------------------------------------
# Persistence across instances
# ---------------------------------------------------------------------------


def test_data_persists_across_instances(tmp_path):
    path = str(tmp_path / "persist_cache")
    c1 = FsBlockCache(path)
    c1.store(Key(value="persist"), Block(data=b"persisted data"))

    c2 = FsBlockCache(path)
    result = c2.get(Key(value="persist"))
    assert result is not None
    assert result.data == b"persisted data"
