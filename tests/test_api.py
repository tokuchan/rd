"""Tests for the ReliableData BlockCache REST API."""

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rd.database import get_db
from rd.main import BLOCK_SIZE, app
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
    stored = base64.b64decode(data["blockData"])
    assert stored[:5] == b"world"
    assert len(stored) == BLOCK_SIZE

    resp = client.get("/blocks/hello")
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert stored[:5] == b"world"
    assert len(stored) == BLOCK_SIZE


def test_put_binary_data(client):
    raw = bytes(range(256))
    b64 = base64.b64encode(raw).decode()
    resp = client.put("/blocks/bin", json={"blockData": b64})
    assert resp.status_code == 200
    returned = base64.b64decode(resp.json()["blockData"])
    assert returned[:256] == raw
    assert len(returned) == BLOCK_SIZE


def test_update_existing_block(client):
    client.put("/blocks/foo", json={"blockData": _b64("bar")})
    client.put("/blocks/foo", json={"blockData": _b64("baz")})
    resp = client.get("/blocks/foo")
    stored = base64.b64decode(resp.json()["blockData"])
    assert stored[:3] == b"baz"
    assert len(stored) == BLOCK_SIZE


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


# ---------------------------------------------------------------------------
# Tests for PUT /file (file-addressed blocks)
# ---------------------------------------------------------------------------


def test_put_file_returns_sha3_block_id(client):
    """PUT /file must return a block ID equal to SHA3-256(bytes.fromhex(contextKey) + path)."""
    from Crypto.Hash import SHA3_256

    # Simulate a hex-encoded context key (public part of an ED25519 data-context key pair)
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    payload = base64.b64encode(b"hello file").decode()
    resp = client.put("/file", json={"contextKey": context_key, "path": "/readme.txt", "blockData": payload})
    assert resp.status_code == 200
    data = resp.json()

    h = SHA3_256.new()
    h.update(bytes.fromhex(context_key))
    h.update(b"/readme.txt")
    expected_id = h.hexdigest()
    assert data["blockID"] == expected_id


def test_put_file_pads_to_block_size(client):
    """PUT /file must pad the stored data to BLOCK_SIZE bytes."""
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    payload = base64.b64encode(b"small").decode()
    resp = client.put("/file", json={"contextKey": context_key, "path": 42, "blockData": payload})
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert len(stored) == BLOCK_SIZE
    assert stored[:5] == b"small"
    assert stored[5:] == b"\x00" * (BLOCK_SIZE - 5)


def test_put_file_integer_path(client):
    """PUT /file must accept an integer path and derive the key consistently."""
    from Crypto.Hash import SHA3_256

    # Simulate a hex-encoded context key (public part of an ED25519 data-context key pair)
    context_key = "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"
    payload = base64.b64encode(b"file metadata").decode()
    resp = client.put("/file", json={"contextKey": context_key, "path": 1001, "blockData": payload})
    assert resp.status_code == 200

    h = SHA3_256.new()
    h.update(bytes.fromhex(context_key))
    h.update(b"1001")
    expected_id = h.hexdigest()
    assert resp.json()["blockID"] == expected_id


def test_put_file_rejects_oversized_block(client):
    """PUT /file must reject data larger than BLOCK_SIZE bytes."""
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    oversized = base64.b64encode(b"x" * (BLOCK_SIZE + 1)).decode()
    resp = client.put("/file", json={"contextKey": context_key, "path": "big", "blockData": oversized})
    assert resp.status_code == 422


def test_put_file_updates_existing_block(client):
    """A second PUT /file to the same key overwrites the first."""
    context_key = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    first = base64.b64encode(b"first").decode()
    second = base64.b64encode(b"second").decode()
    resp1 = client.put("/file", json={"contextKey": context_key, "path": "k", "blockData": first})
    resp2 = client.put("/file", json={"contextKey": context_key, "path": "k", "blockData": second})
    assert resp1.json()["blockID"] == resp2.json()["blockID"]
    stored = base64.b64decode(resp2.json()["blockData"])
    assert stored[:6] == b"second"


# ---------------------------------------------------------------------------
# Tests for PUT /data (content-addressed blocks)
# ---------------------------------------------------------------------------


def _expected_data_block_id(raw: bytes) -> str:
    """Compute the expected block ID for PUT /data (SHA3-256 of the padded block)."""
    from Crypto.Hash import SHA3_256

    padded = raw + b"\x00" * (BLOCK_SIZE - len(raw))
    h = SHA3_256.new()
    h.update(padded)
    return h.hexdigest()


def test_put_data_returns_content_addressed_id(client):
    """PUT /data must return a block ID equal to SHA3-256 of the padded block."""
    raw = b"content addressed"
    payload = base64.b64encode(raw).decode()
    resp = client.put("/data", json={"blockData": payload})
    assert resp.status_code == 200
    assert resp.json()["blockID"] == _expected_data_block_id(raw)


def test_put_data_pads_to_block_size(client):
    """PUT /data must pad data to BLOCK_SIZE bytes."""
    payload = base64.b64encode(b"tiny").decode()
    resp = client.put("/data", json={"blockData": payload})
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert len(stored) == BLOCK_SIZE


def test_put_data_identical_content_same_id(client):
    """Two PUT /data calls with the same content must yield the same block ID."""
    payload = base64.b64encode(b"dedup me").decode()
    resp1 = client.put("/data", json={"blockData": payload})
    resp2 = client.put("/data", json={"blockData": payload})
    assert resp1.json()["blockID"] == resp2.json()["blockID"]


def test_put_data_rejects_oversized_block(client):
    """PUT /data must reject data larger than BLOCK_SIZE bytes."""
    oversized = base64.b64encode(b"x" * (BLOCK_SIZE + 1)).decode()
    resp = client.put("/data", json={"blockData": oversized})
    assert resp.status_code == 422


def test_put_data_exact_block_size_accepted(client):
    """PUT /data must accept data that is exactly BLOCK_SIZE bytes."""
    payload = base64.b64encode(b"z" * BLOCK_SIZE).decode()
    resp = client.put("/data", json={"blockData": payload})
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert stored == b"z" * BLOCK_SIZE
