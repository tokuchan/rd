"""Block format utilities for the ReliableData block store.

This module provides low-level encoding helpers used when constructing
and parsing block payloads.
"""


class ExtendableInteger:
    """An arbitrary-precision non-negative integer encoded as variable-length bytes.

    The encoding follows the same continuation-bit convention used by UTF-8 and
    LEB128 (unsigned):

    * Each byte contributes 7 data bits (the low seven bits).
    * The most-significant bit of each byte is a *continuation* flag:
      ``1`` means another byte follows; ``0`` marks the final byte.
    * Bytes are ordered from least-significant to most-significant group.

    Examples::

        ExtendableInteger(0).asBytes()   == [0x00]
        ExtendableInteger(127).asBytes() == [0x7F]
        ExtendableInteger(128).asBytes() == [0x80, 0x01]
        ExtendableInteger(300).asBytes() == [0xAC, 0x02]
    """

    def __init__(self, value: int) -> None:
        if value < 0:
            raise ValueError("ExtendableInteger only supports non-negative integers")
        self._value = value

    @classmethod
    def fromBytes(cls, data: bytes) -> "ExtendableInteger":
        """Decode an ``ExtendableInteger`` from a sequence of continuation-encoded bytes.

        Only the bytes required to decode one integer are consumed; any trailing
        bytes are ignored.
        """
        value = 0
        shift = 0
        for byte in data:
            value |= (byte & 0x7F) << shift
            shift += 7
            if not (byte & 0x80):
                break
        return cls(value)

    def asInteger(self) -> int:
        """Return the plain Python ``int`` value."""
        return self._value

    def asBytes(self) -> list[int]:
        """Encode the integer as a list of continuation-encoded byte values."""
        value = self._value
        result = []
        while True:
            byte = value & 0x7F
            value >>= 7
            if value != 0:
                byte |= 0x80
            result.append(byte)
            if value == 0:
                break
        return result
