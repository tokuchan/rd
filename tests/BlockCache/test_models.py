"""Tests for BlockCache domain models (Key and Block)."""

import pytest

from rd.BlockCache.errors import BlockTooLargeError
from rd.BlockCache.models import BLOCK_SIZE, Block, Key

# ---------------------------------------------------------------------------
# Key
# ---------------------------------------------------------------------------


def test_key_value():
    k = Key(value="abc")
    assert k.value == "abc"


def test_key_is_frozen():
    k = Key(value="abc")
    with pytest.raises((AttributeError, TypeError)):
        k.value = "other"  # type: ignore[misc]


def test_key_equality():
    assert Key(value="x") == Key(value="x")
    assert Key(value="x") != Key(value="y")


def test_key_hashable():
    """Keys must be usable as dict keys and set members."""
    d = {Key(value="a"): 1, Key(value="b"): 2}
    assert d[Key(value="a")] == 1


# ---------------------------------------------------------------------------
# Block
# ---------------------------------------------------------------------------


def test_block_data():
    b = Block(data=b"hello")
    assert b.data == b"hello"


def test_block_len():
    b = Block(data=b"abc")
    assert len(b) == 3


def test_block_pad_default():
    b = Block(data=b"hi").pad()
    assert len(b.data) == BLOCK_SIZE
    assert b.data[:2] == b"hi"
    assert b.data[2:] == b"\x00" * (BLOCK_SIZE - 2)


def test_block_pad_custom_size():
    b = Block(data=b"xy").pad(block_size=8)
    assert len(b.data) == 8
    assert b.data == b"xy\x00\x00\x00\x00\x00\x00"


def test_block_pad_exact_size():
    data = b"z" * BLOCK_SIZE
    b = Block(data=data).pad()
    assert b.data == data


def test_block_pad_too_large_raises():
    data = b"x" * (BLOCK_SIZE + 1)
    with pytest.raises(BlockTooLargeError):
        Block(data=data).pad()


def test_block_pad_too_large_custom_size_raises():
    with pytest.raises(BlockTooLargeError):
        Block(data=b"hello").pad(block_size=4)


def test_block_pad_returns_new_block():
    original = Block(data=b"a")
    padded = original.pad(block_size=4)
    assert padded is not original
    assert original.data == b"a"  # original unchanged
