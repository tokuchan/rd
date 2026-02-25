"""FastAPI application for the ReliableData BlockCache."""

import base64
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator
from typing import Union

from Crypto.Hash import SHA3_256
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rd.database import get_db, init_db
from rd.models import Store

# Fixed block size (power of two, 4 KiB)
BLOCK_SIZE = 4096


@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncGenerator[None, None]:
    init_db()
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
    contextKey: str  # public part of the owner's data-context key pair (e.g. hex-encoded ED25519 public key)
    path: Union[str, int]
    blockData: str  # base64-encoded binary data, up to BLOCK_SIZE bytes


class DataBlockIn(BaseModel):
    blockData: str  # base64-encoded binary data, up to BLOCK_SIZE bytes


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


def _pad_block(data: bytes) -> bytes:
    """Pad data to BLOCK_SIZE bytes with zero bytes, or reject if too large."""
    if len(data) > BLOCK_SIZE:
        raise HTTPException(
            status_code=422,
            detail=f"blockData exceeds maximum block size of {BLOCK_SIZE} bytes",
        )
    return data + b"\x00" * (BLOCK_SIZE - len(data))


def _file_block_id(context_key: str, path: Union[str, int]) -> str:
    """Derive a block ID by hashing the owner's context key (public key) followed by a path or integer ID."""
    try:
        context_key_bytes = bytes.fromhex(context_key)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail="contextKey must be a valid hex-encoded public key",
        )

    h = SHA3_256.new()
    h.update(context_key_bytes)
    h.update(str(path).encode())
    return h.hexdigest()


def _data_block_id(data: bytes) -> str:
    """Derive a content-addressed block ID as the SHA-3 256 hash of the block data."""
    h = SHA3_256.new()
    h.update(data)
    return h.hexdigest()


def _to_block_out(entry: Store) -> BlockOut:
    return BlockOut(blockID=entry.block_id, blockData=_encode(entry.block_data or b""))


def _upsert(db: Session, block_id: str, data: bytes) -> Store:
    """Insert or update a block in the database and return the refreshed entry."""
    entry = db.get(Store, block_id)
    if entry is None:
        entry = Store(block_id=block_id, block_data=data)
        db.add(entry)
    else:
        entry.block_data = data  # type: ignore[assignment]
    db.commit()
    db.refresh(entry)
    return entry


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/blocks/{blockID}", response_model=BlockOut, summary="Get a block by ID")
def get_block(blockID: str, db: Session = Depends(get_db)) -> BlockOut:
    entry = db.get(Store, blockID)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Block '{blockID}' not found")
    return _to_block_out(entry)


@app.put("/blocks/{blockID}", response_model=BlockOut, summary="Create or update a block")
def put_block(blockID: str, body: BlockIn, db: Session = Depends(get_db)) -> BlockOut:
    raw = _decode(body.blockData)
    padded = _pad_block(raw)
    return _to_block_out(_upsert(db, blockID, padded))


@app.delete("/blocks/{blockID}", status_code=204, summary="Delete a block")
def delete_block(blockID: str, db: Session = Depends(get_db)) -> None:
    entry = db.get(Store, blockID)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Block '{blockID}' not found")
    db.delete(entry)
    db.commit()


@app.put("/file", response_model=BlockOut, summary="Store a file-addressed block (key = SHA3-256(contextKey + path))")
def put_file_block(body: FileBlockIn, db: Session = Depends(get_db)) -> BlockOut:
    """Write a fixed-size block whose ID is derived from the owner's context key and a path/integer."""
    raw = _decode(body.blockData)
    padded = _pad_block(raw)
    block_id = _file_block_id(body.contextKey, body.path)
    return _to_block_out(_upsert(db, block_id, padded))


@app.put("/data", response_model=BlockOut, summary="Store a content-addressed data block (key = SHA3-256(block))")
def put_data_block(body: DataBlockIn, db: Session = Depends(get_db)) -> BlockOut:
    """Write a fixed-size block whose ID is the SHA-3 256 hash of its contents."""
    raw = _decode(body.blockData)
    padded = _pad_block(raw)
    block_id = _data_block_id(padded)
    return _to_block_out(_upsert(db, block_id, padded))
