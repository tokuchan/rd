"""Tests for MagicNumber — keccak-based deterministic PRNG."""

import pytest

from rd.magic_number import MagicNumber

# ---------------------------------------------------------------------------
# Construction — various seed types
# ---------------------------------------------------------------------------


def test_seed_string():
    prng = MagicNumber("hello")
    assert isinstance(prng.blockId(), bytes)


def test_seed_integer():
    prng = MagicNumber(42)
    assert isinstance(prng.blockId(), bytes)


def test_seed_bytes():
    prng = MagicNumber(b"\x00\x01\x02")
    assert isinstance(prng.blockId(), bytes)


def test_seed_bytearray():
    prng = MagicNumber(bytearray(b"\xde\xad\xbe\xef"))
    assert isinstance(prng.blockId(), bytes)


# ---------------------------------------------------------------------------
# bytes() — length and output properties
# ---------------------------------------------------------------------------


def test_bytes_zero_length():
    prng = MagicNumber("seed")
    assert prng.bytes(0) == b""


def test_bytes_exact_block():
    # 256 bits → 32 bytes, exactly one keccak-256 block
    prng = MagicNumber("seed")
    result = prng.bytes(256)
    assert len(result) == 32


def test_bytes_partial_last_byte():
    # 9 bits → 2 bytes; low 7 bits of the second byte must be zero
    prng = MagicNumber("seed")
    result = prng.bytes(9)
    assert len(result) == 2
    assert result[1] & 0x7F == 0, "bits beyond the requested 9 must be cleared"


def test_bytes_non_multiple_of_8():
    # 10 bits → 2 bytes; low 6 bits of last byte masked
    prng = MagicNumber("seed")
    result = prng.bytes(10)
    assert len(result) == 2
    assert result[1] & 0x3F == 0


def test_bytes_multiple_blocks():
    # 512 bits → 64 bytes, requires two keccak blocks
    prng = MagicNumber("seed")
    result = prng.bytes(512)
    assert len(result) == 64


def test_bytes_negative_raises():
    prng = MagicNumber("seed")
    with pytest.raises(ValueError):
        prng.bytes(-1)


# ---------------------------------------------------------------------------
# blockId() — shape and type
# ---------------------------------------------------------------------------


def test_block_id_length():
    prng = MagicNumber("seed")
    bid = prng.blockId()
    assert len(bid) == 32


def test_block_id_returns_bytes():
    prng = MagicNumber("seed")
    assert isinstance(prng.blockId(), bytes)


# ---------------------------------------------------------------------------
# Determinism — same seed → same output
# ---------------------------------------------------------------------------


def test_deterministic_bytes():
    prng1 = MagicNumber("deterministic")
    prng2 = MagicNumber("deterministic")
    assert prng1.bytes(256) == prng2.bytes(256)


def test_deterministic_block_id():
    prng1 = MagicNumber("deterministic")
    prng2 = MagicNumber("deterministic")
    assert prng1.blockId() == prng2.blockId()


def test_deterministic_sequence():
    prng1 = MagicNumber("seq-test")
    prng2 = MagicNumber("seq-test")
    seq1 = [prng1.blockId() for _ in range(5)]
    seq2 = [prng2.blockId() for _ in range(5)]
    assert seq1 == seq2


# ---------------------------------------------------------------------------
# Different seeds → different output
# ---------------------------------------------------------------------------


def test_different_seeds_differ():
    assert MagicNumber("seed-a").blockId() != MagicNumber("seed-b").blockId()


def test_different_int_seeds_differ():
    assert MagicNumber(0).blockId() != MagicNumber(1).blockId()


# ---------------------------------------------------------------------------
# Sequential calls advance the stream
# ---------------------------------------------------------------------------


def test_successive_block_ids_differ():
    prng = MagicNumber("advance-test")
    b1 = prng.blockId()
    b2 = prng.blockId()
    assert b1 != b2


def test_successive_bytes_differ():
    prng = MagicNumber("advance-test")
    r1 = prng.bytes(256)
    r2 = prng.bytes(256)
    assert r1 != r2


def test_stream_is_non_overlapping():
    # Requesting 512 bits in one call vs two 256-bit calls must give same data
    prng1 = MagicNumber("overlap")
    combined = prng1.bytes(512)

    prng2 = MagicNumber("overlap")
    first = prng2.bytes(256)
    second = prng2.bytes(256)

    assert combined == first + second
