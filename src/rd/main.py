"""FastAPI application for the ReliableData BlockCache."""

import base64
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import lru_cache
from typing import Union

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel

from rd.adaptors.sqliteBlockCache import SqliteBlockCache
from rd.BlockCache import useCases
from rd.BlockCache.errors import BlockTooLargeError
from rd.BlockCache.models import BLOCK_SIZE, Block, Key

_DB_URL = os.environ.get("RD_DATABASE_URL", "sqlite:///./rd.db")


@lru_cache(maxsize=1)
def _default_cache() -> SqliteBlockCache:
    """Return the singleton :class:`SqliteBlockCache` for the application."""
    return SqliteBlockCache(_DB_URL)


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    # Ensure the database is initialised before handling requests.
    _default_cache()
    yield


app = FastAPI(
    title="BlockCache",
    description="A reliable block cache exposed via a REST interface.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class BlockIn(BaseModel):
    blockData: str  # base64-encoded binary data


class BlockOut(BaseModel):
    blockID: str
    blockData: str  # base64-encoded binary data

    model_config = {"from_attributes": True}


class FileBlockIn(BaseModel):
    contextKey: str  # public part of the owner's data-context key pair (hex ED25519 public key)
    path: Union[str, int]
    blockData: str  # base64-encoded binary data, up to BLOCK_SIZE bytes


class DataBlockIn(BaseModel):
    blockData: str  # base64-encoded binary data, up to BLOCK_SIZE bytes


# ---------------------------------------------------------------------------
# Dependency
# ---------------------------------------------------------------------------


def get_cache() -> SqliteBlockCache:
    """FastAPI dependency that returns the active block-cache adaptor."""
    return _default_cache()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _decode(data: str) -> bytes:
    try:
        return base64.b64decode(data, validate=True)
    except Exception:
        raise HTTPException(status_code=422, detail="blockData must be valid base64")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/blocks/{blockID}", response_model=BlockOut, summary="Get a block by ID")
def get_block(blockID: str, cache: SqliteBlockCache = Depends(get_cache)) -> BlockOut:
    key = Key(value=blockID)
    block = cache.get(key)
    if block is None:
        raise HTTPException(status_code=404, detail=f"Block '{blockID}' not found")
    return BlockOut(blockID=blockID, blockData=_encode(block.data))


@app.put("/blocks/{blockID}", response_model=BlockOut, summary="Create or update a block")
def put_block(
    blockID: str, body: BlockIn, cache: SqliteBlockCache = Depends(get_cache)
) -> BlockOut:
    raw = _decode(body.blockData)
    try:
        padded = Block(data=raw).pad(BLOCK_SIZE)
    except BlockTooLargeError:
        raise HTTPException(
            status_code=422,
            detail=f"blockData exceeds maximum block size of {BLOCK_SIZE} bytes",
        )
    stored = cache.store(Key(value=blockID), padded)
    return BlockOut(blockID=blockID, blockData=_encode(stored.data))


@app.delete("/blocks/{blockID}", status_code=204, summary="Delete a block")
def delete_block(blockID: str, cache: SqliteBlockCache = Depends(get_cache)) -> None:
    if not cache.delete(Key(value=blockID)):
        raise HTTPException(status_code=404, detail=f"Block '{blockID}' not found")


@app.put(
    "/file",
    response_model=BlockOut,
    summary="Store a file-addressed block (key = SHA3-256(contextKey \u2016 path))",
)
def put_file_block(body: FileBlockIn, cache: SqliteBlockCache = Depends(get_cache)) -> BlockOut:
    """Write a fixed-size block whose ID is derived from the owner's context key
    and a path or integer ID."""
    raw = _decode(body.blockData)
    try:
        key, stored = useCases.store_file_block(cache, body.contextKey, body.path, raw)
    except BlockTooLargeError:
        raise HTTPException(
            status_code=422,
            detail=f"blockData exceeds maximum block size of {BLOCK_SIZE} bytes",
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return BlockOut(blockID=key.value, blockData=_encode(stored.data))


@app.put(
    "/data",
    response_model=BlockOut,
    summary="Store a content-addressed data block (key = SHA3-256(block))",
)
def put_data_block(body: DataBlockIn, cache: SqliteBlockCache = Depends(get_cache)) -> BlockOut:
    """Write a fixed-size block whose ID is the SHA-3 256 hash of its contents."""
    raw = _decode(body.blockData)
    try:
        key, stored = useCases.store_data_block(cache, raw)
    except BlockTooLargeError:
        raise HTTPException(
            status_code=422,
            detail=f"blockData exceeds maximum block size of {BLOCK_SIZE} bytes",
        )
    return BlockOut(blockID=key.value, blockData=_encode(stored.data))
