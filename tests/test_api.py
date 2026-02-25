"""Tests for the ReliableData key/value REST API."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rd.database import get_db
from rd.main import app
from rd.models import Base


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


def test_list_keys_empty(client):
    resp = client.get("/keys")
    assert resp.status_code == 200
    assert resp.json() == []


def test_put_and_get(client):
    resp = client.put("/keys/hello", json={"value": "world"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["key"] == "hello"
    assert data["value"] == "world"

    resp = client.get("/keys/hello")
    assert resp.status_code == 200
    assert resp.json()["value"] == "world"


def test_update_existing_key(client):
    client.put("/keys/foo", json={"value": "bar"})
    client.put("/keys/foo", json={"value": "baz"})
    resp = client.get("/keys/foo")
    assert resp.json()["value"] == "baz"


def test_list_keys_returns_all(client):
    client.put("/keys/a", json={"value": "1"})
    client.put("/keys/b", json={"value": "2"})
    resp = client.get("/keys")
    keys = {e["key"] for e in resp.json()}
    assert keys == {"a", "b"}


def test_get_missing_key(client):
    resp = client.get("/keys/nonexistent")
    assert resp.status_code == 404


def test_delete_key(client):
    client.put("/keys/x", json={"value": "y"})
    resp = client.delete("/keys/x")
    assert resp.status_code == 204

    resp = client.get("/keys/x")
    assert resp.status_code == 404


def test_delete_missing_key(client):
    resp = client.delete("/keys/ghost")
    assert resp.status_code == 404
