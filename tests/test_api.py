"""Tests for the ReliableData BlockCache REST API."""

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rd.database import get_db
from rd.main import app
from rd.models import Base


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def _decode(s: str) -> str:
    return base64.b64decode(s).decode()


@pytest.fixture()
def client(tmp_path):
    """Return a TestClient backed by a fresh in-memory SQLite database."""
    db_url = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_put_and_get(client):
    resp = client.put("/blocks/hello", json={"blockData": _b64("world")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["blockID"] == "hello"
    assert _decode(data["blockData"]) == "world"

    resp = client.get("/blocks/hello")
    assert resp.status_code == 200
    assert _decode(resp.json()["blockData"]) == "world"


def test_put_binary_data(client):
    raw = bytes(range(256))
    b64 = base64.b64encode(raw).decode()
    resp = client.put("/blocks/bin", json={"blockData": b64})
    assert resp.status_code == 200
    returned = base64.b64decode(resp.json()["blockData"])
    assert returned == raw


def test_update_existing_block(client):
    client.put("/blocks/foo", json={"blockData": _b64("bar")})
    client.put("/blocks/foo", json={"blockData": _b64("baz")})
    resp = client.get("/blocks/foo")
    assert _decode(resp.json()["blockData"]) == "baz"


def test_get_missing_block(client):
    resp = client.get("/blocks/nonexistent")
    assert resp.status_code == 404


def test_delete_block(client):
    client.put("/blocks/x", json={"blockData": _b64("y")})
    resp = client.delete("/blocks/x")
    assert resp.status_code == 204

    resp = client.get("/blocks/x")
    assert resp.status_code == 404


def test_delete_missing_block(client):
    resp = client.delete("/blocks/ghost")
    assert resp.status_code == 404


def test_invalid_base64_rejected(client):
    resp = client.put("/blocks/bad", json={"blockData": "not-valid-base64!!!"})
    assert resp.status_code == 422
