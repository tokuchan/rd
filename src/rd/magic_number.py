"""Deterministic hash-derived namespaces for PRNG-generated data.

`MagicNumber` hashes an input seed into an internal state, then derives
new independent states using an incrementing counter. Each derivation can
be materialized as:

- another `MagicNumber` (for hierarchy/branching),
- a `HashBlocks` view (an indexable infinite list), or
- a `HashRange` view (an indexable finite list).

The hashing algorithm is pluggable via a hash-factory callable and defaults
to `hashlib.sha3_256`.
"""

import hashlib
from dataclasses import dataclass
from typing import Callable

HashFactory = Callable[[], "hashlib._Hash"]


def _normalizeSeed(seed) -> bytes:
    if isinstance(seed, int):
        byteLength = (seed.bit_length() + 7) // 8 or 1
        return seed.to_bytes(byteLength, "big")
    if isinstance(seed, str):
        return seed.encode("utf-8")
    if isinstance(seed, (bytes, bytearray)):
        return bytes(seed)
    return str(seed).encode("utf-8")


def _hashBytes(payload: bytes, hashFactory: HashFactory) -> bytes:
    hasher = hashFactory()
    hasher.update(payload)
    return hasher.digest()


@dataclass
class HashBlocks:
    """Deterministically-generated, indexable pseudorandom hash blocks."""

    state: bytes
    hashFactory: HashFactory = hashlib.sha3_256

    def get(self, index: int) -> bytes:
        """Return the block at `index` in the deterministic pseudo-list.

        >>> hb = HashBlocks(b"hello world")
        >>> hb.get(0) == hb.get(0)
        True
        >>> hb.get(0) != hb.get(1)
        True
        >>> len(hb.get(0))
        32
        """
        if index < 0:
            raise IndexError(f"Index {index} < 0.")

        indexLength = (index.bit_length() + 7) // 8 or 1
        indexBytes = index.to_bytes(indexLength, "big")
        return _hashBytes(self.state + indexBytes, self.hashFactory)

    def __getitem__(self, index: int) -> bytes:
        """Return the block at `index` in the deterministic pseudo-list.

        >>> hb = HashBlocks(b"hello world")
        >>> hb[0] == hb.get(0)
        True
        >>> hb[1] == hb.get(1)
        True
        """
        return self.get(index)


@dataclass
class HashRange:
    """Finite-length deterministic range over `HashBlocks`."""

    state: bytes
    limit: int
    hashFactory: HashFactory = hashlib.sha3_256

    def get(self, index: int) -> bytes:
        """Return the block at `index`, bounded by `limit`.

        >>> hr = HashRange(b"hello world", 5)
        >>> hr.get(0) == hr.get(0)
        True
        >>> hr.get(0) != hr.get(1)
        True
        >>> HashRange(b"hello world", 5).get(5)
        Traceback (most recent call last):
        ...
        IndexError: Index 5 >= 5.
        >>> HashRange(b"hello world", 5).get(15)
        Traceback (most recent call last):
        ...
        IndexError: Index 15 >= 5.
        """
        if index < 0:
            raise IndexError(f"Index {index} < 0.")
        if index >= self.limit:
            raise IndexError(f"Index {index} >= {self.limit}.")

        return HashBlocks(self.state, self.hashFactory).get(index)

    def __getitem__(self, index: int) -> bytes:
        """Return the block at `index`, bounded by `limit`.

        >>> hr = HashRange(b"hello world", 5)
        >>> hr[0] == hr.get(0)
        True
        >>> hr[1] == hr.get(1)
        True
        >>> HashRange(b"hello world", 5)[5]
        Traceback (most recent call last):
        ...
        IndexError: Index 5 >= 5.
        >>> HashRange(b"hello world", 5)[15]
        Traceback (most recent call last):
        ...
        IndexError: Index 15 >= 5.
        """
        return self.get(index)


class MagicNumber:
    """Deterministic state derivation for `HashBlocks` and `HashRange`.

    Typical usage:

    1. Construct one `MagicNumber` from a seed.
    2. Derive one or more child `MagicNumber` instances.
    3. Materialize `HashBlocks`/`HashRange` views from any branch.

    Every derivation call advances an internal counter, so each returned
    object receives a unique derived state.

    >>> root = MagicNumber("my-secret-seed")
    >>> branch = root.deriveMagicNumber()
    >>> blocks = root.deriveHashBlocks()
    >>> bounded = branch.deriveHashRange(3)
    >>> len(blocks[0])
    32
    >>> len(bounded[1])
    32
    """

    def __init__(self, seed, hashFactory: HashFactory = hashlib.sha3_256) -> None:
        self._hashFactory = hashFactory
        self._state: bytes = _hashBytes(_normalizeSeed(seed), self._hashFactory)
        self._counter: int = 0

    @classmethod
    def _fromState(cls, state: bytes, hashFactory: HashFactory) -> "MagicNumber":
        instance = cls.__new__(cls)
        instance._hashFactory = hashFactory
        instance._state = state
        instance._counter = 0
        return instance

    def _nextState(self) -> bytes:
        counterBytes = self._counter.to_bytes(8, "big")
        derivedState = _hashBytes(self._state + counterBytes, self._hashFactory)
        self._counter += 1
        return derivedState

    def deriveMagicNumber(self) -> "MagicNumber":
        """Derive and return a child `MagicNumber` with a fresh state.

        >>> root = MagicNumber("seed")
        >>> c1 = root.deriveMagicNumber()
        >>> c2 = root.deriveMagicNumber()
        >>> c1.deriveHashBlocks()[0] != c2.deriveHashBlocks()[0]
        True
        """
        return MagicNumber._fromState(self._nextState(), self._hashFactory)

    def deriveHashBlocks(self) -> HashBlocks:
        """Derive and return a fresh `HashBlocks` view.

        >>> m = MagicNumber("seed")
        >>> blocks = m.deriveHashBlocks()
        >>> isinstance(blocks, HashBlocks)
        True
        """
        return HashBlocks(self._nextState(), self._hashFactory)

    def deriveHashRange(self, limit: int) -> HashRange:
        """Derive and return a fresh bounded `HashRange` view.

        >>> m = MagicNumber("seed")
        >>> r = m.deriveHashRange(2)
        >>> isinstance(r, HashRange)
        True
        >>> r.limit
        2
        """
        if limit < 0:
            raise ValueError("limit must be non-negative")
        return HashRange(self._nextState(), limit, self._hashFactory)
