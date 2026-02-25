"""FastAPI application for the ReliableData BlockCache."""

import base64
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from rd.database import get_db, init_db
from rd.models import Store


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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _decode(data: str) -> bytes:
    try:
        return base64.b64decode(data)
    except Exception:
        raise HTTPException(status_code=422, detail="blockData must be valid base64")


def _to_block_out(entry: Store) -> BlockOut:
    return BlockOut(blockID=entry.block_id, blockData=_encode(entry.block_data or b""))


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
    entry = db.get(Store, blockID)
    if entry is None:
        entry = Store(block_id=blockID, block_data=raw)
        db.add(entry)
    else:
        entry.block_data = raw  # type: ignore[assignment]
    db.commit()
    db.refresh(entry)
    return _to_block_out(entry)


@app.delete("/blocks/{blockID}", status_code=204, summary="Delete a block")
def delete_block(blockID: str, db: Session = Depends(get_db)) -> None:
    entry = db.get(Store, blockID)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Block '{blockID}' not found")
    db.delete(entry)
    db.commit()
