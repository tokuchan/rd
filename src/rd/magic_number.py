"""Keccak-based deterministic PRNG (sponge construction).

``MagicNumber`` absorbs a seed value into a keccak-256 state and then
provides an unlimited stream of pseudo-random bytes by repeatedly
hashing the internal state with a monotonically-increasing counter
(counter-mode keccak squeeze).
"""

import math
from dataclasses import dataclass

from Crypto.Hash import keccak as _keccak


@dataclass
class HashBlocks:
    """A deterministically-generated "collection" of pseudorandom 256-bit blocks."""

    state: bytes
    BLOCK_BITS: int = 256

    def get(self, index: int) -> bytes:
        """Given an index i, return the ith 256-bit block in the pseudocollection.

        >>> HashBlocks(b"hello world").get(0)
        b"\\xca\\xfb\\xcfZ5n\\xd1\\xc2\\x13c;'v\\xc5\\xba\\xca\\x9c\\x06jc\\x10:\\xa3\\xe4\\x16\\xaf\\x9a\\xa2\\xe0G\\xdc\\x87"

        >>> HashBlocks(b"hello world").get(1)
        b'\\x899P\\xfc\\xd57a\\x89/\\xe4\\x8f\\xc4\\xb5?K\\xc9\\xfe1\\xaa\\x88!\\xf1)\\xb4\\xc6\\xc9{:\\xa0\\xb7\\x14B'

        >>> HashBlocks(b"hello world").get(0)
        b"\\xca\\xfb\\xcfZ5n\\xd1\\xc2\\x13c;'v\\xc5\\xba\\xca\\x9c\\x06jc\\x10:\\xa3\\xe4\\x16\\xaf\\x9a\\xa2\\xe0G\\xdc\\x87"
        """

        h = _keccak.new(digest_bits=self.BLOCK_BITS)
        h.update(self.state)
        indexLength = (index.bit_length() + 7) // 8 or 1  # at least 1 byte for seed == 0
        indexBytes: bytes = index.to_bytes(indexLength, "big")
        h.update(indexBytes)
        return h.digest()

    def __getitem__(self, index: int) -> bytes:
        """Given an index i, return the ith 256-bit block in the pseudocollection.

        >>> HashBlocks(b"hello world")[0]
        b"\\xca\\xfb\\xcfZ5n\\xd1\\xc2\\x13c;'v\\xc5\\xba\\xca\\x9c\\x06jc\\x10:\\xa3\\xe4\\x16\\xaf\\x9a\\xa2\\xe0G\\xdc\\x87"

        >>> HashBlocks(b"hello world")[1]
        b'\\x899P\\xfc\\xd57a\\x89/\\xe4\\x8f\\xc4\\xb5?K\\xc9\\xfe1\\xaa\\x88!\\xf1)\\xb4\\xc6\\xc9{:\\xa0\\xb7\\x14B'

        >>> HashBlocks(b"hello world")[0]
        b"\\xca\\xfb\\xcfZ5n\\xd1\\xc2\\x13c;'v\\xc5\\xba\\xca\\x9c\\x06jc\\x10:\\xa3\\xe4\\x16\\xaf\\x9a\\xa2\\xe0G\\xdc\\x87"
        """
        return self.get(index)
class MagicNumber:
    """A deterministic PRNG seeded via the keccak-256 sponge function.

    The seed may be an :class:`int`, :class:`str`, :class:`bytes`, or
    :class:`bytearray`.  Successive calls to :meth:`bytes` or
    :meth:`blockId` advance the internal counter so each call returns a
    distinct, non-overlapping slice of the pseudo-random stream.

    Example::

        prng = MagicNumber("my-secret-seed")
        block_a = prng.blockId()   # first 256-bit block ID
        block_b = prng.blockId()   # second, different 256-bit block ID
    """

    _BLOCK_BITS = 256
    _BLOCK_BYTES = _BLOCK_BITS // 8

    def __init__(self, seed) -> None:
        if isinstance(seed, int):
            byte_length = (seed.bit_length() + 7) // 8 or 1  # at least 1 byte for seed == 0
            seed_bytes: bytes = seed.to_bytes(byte_length, "big")
        elif isinstance(seed, str):
            seed_bytes = seed.encode("utf-8")
        elif isinstance(seed, (bytes, bytearray)):
            seed_bytes = bytes(seed)
        else:
            seed_bytes = str(seed).encode("utf-8")

        k = _keccak.new(digest_bits=self._BLOCK_BITS)
        k.update(seed_bytes)
        self._state: bytes = k.digest()
        self._counter: int = 0
        self._buf: bytearray = bytearray()  # unconsumed bytes from the last squeeze block

    def bytes(self, length: int) -> bytes:
        """Squeeze *length* bits from the sponge.

        Returns ``ceil(length / 8)`` bytes.  If *length* is not a multiple
        of 8 the final byte is zero-padded (masked) to align to a byte
        boundary.

        Each call advances the internal counter so successive calls produce
        non-overlapping output.

        :param length: Number of bits to squeeze (non-negative).
        :raises ValueError: If *length* is negative.
        """
        if length < 0:
            raise ValueError("length must be non-negative")

        byte_count = math.ceil(length / 8)
        while len(self._buf) < byte_count:
            k = _keccak.new(digest_bits=self._BLOCK_BITS)
            k.update(self._state)
            k.update(self._counter.to_bytes(8, "big"))
            self._buf.extend(k.digest())
            self._counter += 1

        output = bytearray(self._buf[:byte_count])
        self._buf = self._buf[byte_count:]

        leftover_bits = length % 8
        if leftover_bits != 0:
            mask = (0xFF << (8 - leftover_bits)) & 0xFF
            output[-1] = output[-1] & mask

        return bytes(output)

    def blockId(self) -> bytes:
        """Return a 256-bit (32-byte) block ID squeezed from the sponge."""
        return self.bytes(256)
