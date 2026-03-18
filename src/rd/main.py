"""FastAPI application for the ReliableData BlockCache."""

import base64
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Union

from Crypto.Hash import SHA3_256
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rd.database import getDb, initDb
from rd.models import Store

# Fixed block size (power of two, 4 KiB)
BlockSize = 4096


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    initDb()
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
    blockData: str  # base64-encoded binary data, up to BlockSize bytes


class DataBlockIn(BaseModel):
    blockData: str  # base64-encoded binary data, up to BlockSize bytes


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


def _padBlock(data: bytes) -> bytes:
    """Pad data to BlockSize bytes with zero bytes, or reject if too large."""
    if len(data) > BlockSize:
        raise HTTPException(
            status_code=422,
            detail=f"blockData exceeds maximum block size of {BlockSize} bytes",
        )
    return data + b"\x00" * (BlockSize - len(data))


def _fileBlockId(contextKey: str, path: Union[str, int]) -> str:
    """Derive a block ID by hashing the owner's context key followed by a path or integer ID."""
    try:
        contextKeyBytes = bytes.fromhex(contextKey)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="contextKey must be a valid hex-encoded public key",
        )

    h = SHA3_256.new()
    h.update(contextKeyBytes)
    h.update(str(path).encode())
    return h.hexdigest()


def _dataBlockId(data: bytes) -> str:
    """Derive a content-addressed block ID as the SHA-3 256 hash of the block data."""
    h = SHA3_256.new()
    h.update(data)
    return h.hexdigest()


def _toBlockOut(entry: Store) -> BlockOut:
    return BlockOut(blockID=entry.blockId, blockData=_encode(entry.blockData or b""))


def _upsert(db: Session, blockId: str, data: bytes) -> Store:
    """Insert or update a block in the database and return the refreshed entry."""
    entry = db.get(Store, blockId)
    if entry is None:
        entry = Store(blockId=blockId, blockData=data)
        db.add(entry)
    else:
        entry.blockData = data  # type: ignore[assignment]
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/blocks/{blockID}", response_model=BlockOut, summary="Get a block by ID")
def getBlock(blockID: str, db: Session = Depends(getDb)) -> BlockOut:
    entry = db.get(Store, blockID)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Block '{blockID}' not found")
    return _toBlockOut(entry)


@app.put("/blocks/{blockID}", response_model=BlockOut, summary="Create or update a block")
def putBlock(blockID: str, body: BlockIn, db: Session = Depends(getDb)) -> BlockOut:
    raw = _decode(body.blockData)
    padded = _padBlock(raw)
    return _toBlockOut(_upsert(db, blockID, padded))


@app.delete("/blocks/{blockID}", status_code=204, summary="Delete a block")
def deleteBlock(blockID: str, db: Session = Depends(getDb)) -> None:
    entry = db.get(Store, blockID)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Block '{blockID}' not found")
    db.delete(entry)
    db.commit()


@app.put(
    "/file",
    response_model=BlockOut,
    summary="Store a file-addressed block (key = SHA3-256(contextKey + path))",
)
def putFileBlock(body: FileBlockIn, db: Session = Depends(getDb)) -> BlockOut:
    """Write a fixed-size block whose ID is derived from the owner's context key
    and a path or integer ID."""
    raw = _decode(body.blockData)
    padded = _padBlock(raw)
    blockId = _fileBlockId(body.contextKey, body.path)
    return _toBlockOut(_upsert(db, blockId, padded))


@app.put(
    "/data",
    response_model=BlockOut,
    summary="Store a content-addressed data block (key = SHA3-256(block))",
)
def putDataBlock(body: DataBlockIn, db: Session = Depends(getDb)) -> BlockOut:
    """Write a fixed-size block whose ID is the SHA-3 256 hash of its contents."""
    raw = _decode(body.blockData)
    padded = _padBlock(raw)
    blockId = _dataBlockId(padded)
    return _toBlockOut(_upsert(db, blockId, padded))
