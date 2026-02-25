"""FastAPI application for the ReliableData key/value store."""

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
    title="ReliableData",
    description="A SQLite3-backed key/value store exposed via a REST interface.",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Request / response schemas
# ---------------------------------------------------------------------------


class ValueIn(BaseModel):
    value: str


class EntryOut(BaseModel):
    key: str
    value: str

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/keys", response_model=list[EntryOut], summary="List all entries")
def list_keys(db: Session = Depends(get_db)) -> list[Store]:
    return db.query(Store).all()


@app.get("/keys/{key}", response_model=EntryOut, summary="Get a value by key")
def get_key(key: str, db: Session = Depends(get_db)) -> Store:
    entry = db.get(Store, key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    return entry


@app.put("/keys/{key}", response_model=EntryOut, summary="Create or update a key/value pair")
def put_key(key: str, body: ValueIn, db: Session = Depends(get_db)) -> Store:
    entry = db.get(Store, key)
    if entry is None:
        entry = Store(key=key, value=body.value)
        db.add(entry)
    else:
        entry.value = body.value  # type: ignore[assignment]
    db.commit()
    db.refresh(entry)
    return entry


@app.delete("/keys/{key}", status_code=204, summary="Delete a key/value pair")
def delete_key(key: str, db: Session = Depends(get_db)) -> None:
    entry = db.get(Store, key)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Key '{key}' not found")
    db.delete(entry)
    db.commit()
