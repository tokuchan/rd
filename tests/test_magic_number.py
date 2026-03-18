"""Tests for MagicNumber deterministic state derivation."""

import hashlib

import pytest

from rd.magic_number import HashBlocks, HashRange, MagicNumber

# ---------------------------------------------------------------------------
# Construction — various seed types
# ---------------------------------------------------------------------------


def testSeedString():
    prng = MagicNumber("hello")
    assert isinstance(prng.deriveMagicNumber(), MagicNumber)


def testSeedInteger():
    prng = MagicNumber(42)
    assert isinstance(prng.deriveHashBlocks(), HashBlocks)


def testSeedBytes():
    prng = MagicNumber(b"\x00\x01\x02")
    assert isinstance(prng.deriveHashRange(1), HashRange)


def testSeedBytearray():
    prng = MagicNumber(bytearray(b"\xde\xad\xbe\xef"))
    assert isinstance(prng.deriveHashBlocks(), HashBlocks)


def testSeedFallbackToStringRepresentation():
    class SeedObject:
        def __str__(self) -> str:
            return "custom-seed"

    objectSeedValue = MagicNumber(SeedObject()).deriveHashBlocks()[0]
    stringSeedValue = MagicNumber("custom-seed").deriveHashBlocks()[0]
    assert objectSeedValue == stringSeedValue


# ---------------------------------------------------------------------------
# HashBlocks / HashRange output behavior
# ---------------------------------------------------------------------------


def testHashBlocksGetAndIndexMatch():
    blocks = MagicNumber("seed").deriveHashBlocks()
    assert blocks.get(0) == blocks[0]


def testHashBlocksValuesAreDigestSized():
    blocks = MagicNumber("seed").deriveHashBlocks()
    assert len(blocks[0]) == hashlib.sha3_256().digest_size


def testHashRangeGetAndIndexMatch():
    rng = MagicNumber("seed").deriveHashRange(5)
    assert rng.get(3) == rng[3]


def testHashRangeOutOfBoundsRaises():
    rng = MagicNumber("seed").deriveHashRange(2)
    with pytest.raises(IndexError):
        _ = rng[2]


def testHashBlocksNegativeIndexRaises():
    blocks = MagicNumber("seed").deriveHashBlocks()
    with pytest.raises(IndexError):
        _ = blocks[-1]


def testHashRangeNegativeIndexRaises():
    rng = MagicNumber("seed").deriveHashRange(2)
    with pytest.raises(IndexError):
        _ = rng[-1]


def testHashRangeNegativeLimitRaises():
    prng = MagicNumber("seed")
    with pytest.raises(ValueError):
        prng.deriveHashRange(-1)


# ---------------------------------------------------------------------------
# Determinism — same seed and derivation shape -> same output
# ---------------------------------------------------------------------------


def testDeterministicHashBlocksFirstValue():
    prng1 = MagicNumber("deterministic")
    prng2 = MagicNumber("deterministic")
    assert prng1.deriveHashBlocks()[0] == prng2.deriveHashBlocks()[0]


def testDeterministicHashRangeValue():
    prng1 = MagicNumber("deterministic")
    prng2 = MagicNumber("deterministic")
    assert prng1.deriveHashRange(5)[4] == prng2.deriveHashRange(5)[4]


def testDeterministicChildMagicNumberFlow():
    parent1 = MagicNumber("deterministic")
    parent2 = MagicNumber("deterministic")
    child1 = parent1.deriveMagicNumber()
    child2 = parent2.deriveMagicNumber()
    assert child1.deriveHashBlocks()[0] == child2.deriveHashBlocks()[0]


# ---------------------------------------------------------------------------
# Different seeds -> different output
# ---------------------------------------------------------------------------


def testDifferentSeedsDiffer():
    assert (
        MagicNumber("seed-a").deriveHashBlocks()[0] != MagicNumber("seed-b").deriveHashBlocks()[0]
    )


def testDifferentIntSeedsDiffer():
    assert MagicNumber(0).deriveHashBlocks()[0] != MagicNumber(1).deriveHashBlocks()[0]


# ---------------------------------------------------------------------------
# Sequential derivations advance state
# ---------------------------------------------------------------------------


def testSuccessiveHashBlocksAreDistinct():
    prng = MagicNumber("seed")
    first = prng.deriveHashBlocks()[0]
    second = prng.deriveHashBlocks()[0]
    assert first != second


def testSuccessiveHashRangesAreDistinct():
    prng = MagicNumber("seed")
    first = prng.deriveHashRange(3)[0]
    second = prng.deriveHashRange(3)[0]
    assert first != second


def testSuccessiveChildMagicNumbersAreDistinct():
    prng = MagicNumber("advance-test")
    child1 = prng.deriveMagicNumber()
    child2 = prng.deriveMagicNumber()

    value1 = child1.deriveHashBlocks()[0]
    value2 = child2.deriveHashBlocks()[0]
    assert value1 != value2


def testGeneralUsagePatternBranchingIsDeterministic():
    rootA = MagicNumber("tree-seed")
    rootB = MagicNumber("tree-seed")

    branchA = rootA.deriveMagicNumber()
    branchB = rootB.deriveMagicNumber()

    rootBlocksA = rootA.deriveHashBlocks()
    rootBlocksB = rootB.deriveHashBlocks()
    branchRangeA = branchA.deriveHashRange(4)
    branchRangeB = branchB.deriveHashRange(4)

    assert rootBlocksA[2] == rootBlocksB[2]
    assert branchRangeA[3] == branchRangeB[3]


def testPluggableHashAlgorithmChangesOutput():
    defaultValue = MagicNumber("pluggable-seed").deriveHashBlocks()[0]
    sha256Value = MagicNumber("pluggable-seed", hashFactory=hashlib.sha256).deriveHashBlocks()[0]
    assert defaultValue != sha256Value


def testPluggableHashAlgorithmIsDeterministic():
    first = MagicNumber("pluggable-seed", hashFactory=hashlib.sha256).deriveHashBlocks()[0]
    second = MagicNumber("pluggable-seed", hashFactory=hashlib.sha256).deriveHashBlocks()[0]
    assert first == second
