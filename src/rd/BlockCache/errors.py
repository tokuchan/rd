"""Domain-specific errors for the BlockCache."""


class BlockNotFoundError(KeyError):
    """Raised when a requested block is not found in the cache."""


class BlockTooLargeError(ValueError):
    """Raised when block data exceeds the maximum allowed block size."""
