"""Tests for the ReliableData BlockCache REST API."""

import base64

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rd.database import getDb
from rd.main import BlockSize, app
from rd.models import Base

# TODO: import hashlib once CSPRNG / key-derivation helpers are added (reserved for future use)


def _b64(s: str) -> str:
    return base64.b64encode(s.encode()).decode()


def _decode(s: str) -> str:
    return base64.b64decode(s).decode()


@pytest.fixture()
def client(tmp_path):
    """Return a TestClient backed by a fresh in-memory SQLite database."""
    dbUrl = f"sqlite:///{tmp_path}/test.db"
    engine = create_engine(dbUrl, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def overrideGetDb():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[getDb] = overrideGetDb
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
    engine.dispose()


def testPutAndGet(client):
    resp = client.put("/blocks/hello", json={"blockData": _b64("world")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["blockID"] == "hello"
    stored = base64.b64decode(data["blockData"])
    assert stored[:5] == b"world"
    assert len(stored) == BlockSize

    resp = client.get("/blocks/hello")
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert stored[:5] == b"world"
    assert len(stored) == BlockSize


def testPutBinaryData(client):
    raw = bytes(range(256))
    b64 = base64.b64encode(raw).decode()
    resp = client.put("/blocks/bin", json={"blockData": b64})
    assert resp.status_code == 200
    returned = base64.b64decode(resp.json()["blockData"])
    assert returned[:256] == raw
    assert len(returned) == BlockSize


def testUpdateExistingBlock(client):
    client.put("/blocks/foo", json={"blockData": _b64("bar")})
    client.put("/blocks/foo", json={"blockData": _b64("baz")})
    resp = client.get("/blocks/foo")
    stored = base64.b64decode(resp.json()["blockData"])
    assert stored[:3] == b"baz"
    assert len(stored) == BlockSize


def testGetMissingBlock(client):
    resp = client.get("/blocks/nonexistent")
    assert resp.status_code == 404


def testDeleteBlock(client):
    client.put("/blocks/x", json={"blockData": _b64("y")})
    resp = client.delete("/blocks/x")
    assert resp.status_code == 204

    resp = client.get("/blocks/x")
    assert resp.status_code == 404


def testDeleteMissingBlock(client):
    resp = client.delete("/blocks/ghost")
    assert resp.status_code == 404


def testInvalidBase64Rejected(client):
    resp = client.put("/blocks/bad", json={"blockData": "not-valid-base64!!!"})
    assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Tests for PUT /file (file-addressed blocks)
# ---------------------------------------------------------------------------


def testPutFileReturnsSha3BlockId(client):
    """PUT /file must return a block ID equal to SHA3-256(bytes.fromhex(contextKey) + path)."""
    from Crypto.Hash import SHA3_256

    # Simulate a hex-encoded context key (public part of an ED25519 data-context key pair)
    contextKey = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    payload = base64.b64encode(b"hello file").decode()
    resp = client.put(
        "/file", json={"contextKey": contextKey, "path": "/readme.txt", "blockData": payload}
    )
    assert resp.status_code == 200
    data = resp.json()

    h = SHA3_256.new()
    h.update(bytes.fromhex(contextKey))
    h.update(b"/readme.txt")
    expectedId = h.hexdigest()
    assert data["blockID"] == expectedId


def testPutFilePadsToBlockSize(client):
    """PUT /file must pad the stored data to BlockSize bytes."""
    contextKey = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    payload = base64.b64encode(b"small").decode()
    resp = client.put("/file", json={"contextKey": contextKey, "path": 42, "blockData": payload})
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert len(stored) == BlockSize
    assert stored[:5] == b"small"
    assert stored[5:] == b"\x00" * (BlockSize - 5)


def testPutFileIntegerPath(client):
    """PUT /file must accept an integer path and derive the key consistently."""
    from Crypto.Hash import SHA3_256

    # Simulate a hex-encoded context key (public part of an ED25519 data-context key pair)
    contextKey = "3b6a27bcceb6a42d62a3a8d02a6f0d73653215771de243a63ac048a18b59da29"
    payload = base64.b64encode(b"file metadata").decode()
    resp = client.put("/file", json={"contextKey": contextKey, "path": 1001, "blockData": payload})
    assert resp.status_code == 200

    h = SHA3_256.new()
    h.update(bytes.fromhex(contextKey))
    h.update(b"1001")
    expectedId = h.hexdigest()
    assert resp.json()["blockID"] == expectedId


def testPutFileRejectsOversizedBlock(client):
    """PUT /file must reject data larger than BlockSize bytes."""
    contextKey = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    oversized = base64.b64encode(b"x" * (BlockSize + 1)).decode()
    resp = client.put(
        "/file", json={"contextKey": contextKey, "path": "big", "blockData": oversized}
    )
    assert resp.status_code == 422


def testPutFileRejectsInvalidContextKey(client):
    payload = base64.b64encode(b"small").decode()
    resp = client.put("/file", json={"contextKey": "not-hex", "path": "x", "blockData": payload})
    assert resp.status_code == 422
    assert "valid hex-encoded public key" in resp.json()["detail"]


def testPutFileUpdatesExistingBlock(client):
    """A second PUT /file to the same key overwrites the first."""
    contextKey = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    first = base64.b64encode(b"first").decode()
    second = base64.b64encode(b"second").decode()
    resp1 = client.put("/file", json={"contextKey": contextKey, "path": "k", "blockData": first})
    resp2 = client.put("/file", json={"contextKey": contextKey, "path": "k", "blockData": second})
    assert resp1.json()["blockID"] == resp2.json()["blockID"]
    stored = base64.b64decode(resp2.json()["blockData"])
    assert stored[:6] == b"second"


# ---------------------------------------------------------------------------
# Tests for PUT /data (content-addressed blocks)
# ---------------------------------------------------------------------------


def _expectedDataBlockId(raw: bytes) -> str:
    """Compute the expected block ID for PUT /data (SHA3-256 of the padded block)."""
    from Crypto.Hash import SHA3_256

    padded = raw + b"\x00" * (BlockSize - len(raw))
    h = SHA3_256.new()
    h.update(padded)
    return h.hexdigest()


def testPutDataReturnsContentAddressedId(client):
    """PUT /data must return a block ID equal to SHA3-256 of the padded block."""
    raw = b"content addressed"
    payload = base64.b64encode(raw).decode()
    resp = client.put("/data", json={"blockData": payload})
    assert resp.status_code == 200
    assert resp.json()["blockID"] == _expectedDataBlockId(raw)


def testPutDataPadsToBlockSize(client):
    """PUT /data must pad data to BlockSize bytes."""
    payload = base64.b64encode(b"tiny").decode()
    resp = client.put("/data", json={"blockData": payload})
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert len(stored) == BlockSize


def testPutDataIdenticalContentSameId(client):
    """Two PUT /data calls with the same content must yield the same block ID."""
    payload = base64.b64encode(b"dedup me").decode()
    resp1 = client.put("/data", json={"blockData": payload})
    resp2 = client.put("/data", json={"blockData": payload})
    assert resp1.json()["blockID"] == resp2.json()["blockID"]


def testPutDataRejectsOversizedBlock(client):
    """PUT /data must reject data larger than BlockSize bytes."""
    oversized = base64.b64encode(b"x" * (BlockSize + 1)).decode()
    resp = client.put("/data", json={"blockData": oversized})
    assert resp.status_code == 422


def testPutDataExactBlockSizeAccepted(client):
    """PUT /data must accept data that is exactly BlockSize bytes."""
    payload = base64.b64encode(b"z" * BlockSize).decode()
    resp = client.put("/data", json={"blockData": payload})
    assert resp.status_code == 200
    stored = base64.b64decode(resp.json()["blockData"])
    assert stored == b"z" * BlockSize
