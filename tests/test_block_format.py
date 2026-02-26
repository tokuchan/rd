"""Tests for block format utilities (ExtendableInteger)."""

import pytest

from rd.block_format import ExtendableInteger

# ---------------------------------------------------------------------------
# Construction from a plain integer
# ---------------------------------------------------------------------------


def test_zero():
    ei = ExtendableInteger(0)
    assert ei.asInteger() == 0
    assert ei.asBytes() == [0x00]


def test_small_value():
    ei = ExtendableInteger(1)
    assert ei.asInteger() == 1
    assert ei.asBytes() == [0x01]


def test_max_single_byte():
    ei = ExtendableInteger(127)
    assert ei.asInteger() == 127
    assert ei.asBytes() == [0x7F]


def test_first_two_byte_value():
    ei = ExtendableInteger(128)
    assert ei.asInteger() == 128
    assert ei.asBytes() == [0x80, 0x01]


def test_three_hundred():
    # 300 = 0b100101100; 7-bit groups LSB-first: 0b0101100 (44), 0b10 (2)
    ei = ExtendableInteger(300)
    assert ei.asInteger() == 300
    assert ei.asBytes() == [0xAC, 0x02]


def test_large_value():
    value = 2**21 - 1  # three full 7-bit groups
    ei = ExtendableInteger(value)
    assert ei.asInteger() == value
    assert len(ei.asBytes()) == 3


def test_arbitrary_large_value():
    value = 10**18
    ei = ExtendableInteger(value)
    assert ei.asInteger() == value


def test_negative_raises():
    with pytest.raises(ValueError):
        ExtendableInteger(-1)


# ---------------------------------------------------------------------------
# Round-trip: asBytes -> fromBytes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("value", [0, 1, 63, 127, 128, 255, 300, 16383, 16384, 2**32, 10**15])
def test_round_trip(value):
    ei = ExtendableInteger(value)
    decoded = ExtendableInteger.fromBytes(bytes(ei.asBytes()))
    assert decoded.asInteger() == value


# ---------------------------------------------------------------------------
# fromBytes
# ---------------------------------------------------------------------------


def test_from_bytes_single():
    ei = ExtendableInteger.fromBytes(bytes([0x7F]))
    assert ei.asInteger() == 127


def test_from_bytes_two_bytes():
    ei = ExtendableInteger.fromBytes(bytes([0x80, 0x01]))
    assert ei.asInteger() == 128


def test_from_bytes_ignores_trailing():
    # Extra bytes after the terminating byte should be ignored
    ei = ExtendableInteger.fromBytes(bytes([0x01, 0xFF, 0xFF]))
    assert ei.asInteger() == 1


def test_from_bytes_300():
    ei = ExtendableInteger.fromBytes(bytes([0xAC, 0x02]))
    assert ei.asInteger() == 300
