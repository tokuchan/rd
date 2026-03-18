"""ApprovalTests-based snapshot tests for CLI and API behaviors."""

import base64
import json
from pathlib import Path

from approvaltests import verify
from click.testing import CliRunner
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rd.cli import main
from rd.database import getDb
from rd.main import BlockSize, app
from rd.models import Base


def _makeClient(tmpPath: Path) -> TestClient:
    dbUrl = f"sqlite:///{tmpPath}/approval-tests.db"
    engine = create_engine(dbUrl, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    testingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    def overrideGetDb():
        db = testingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[getDb] = overrideGetDb
    return TestClient(app)


def testCliHelpApproval():
    runner = CliRunner()
    result = runner.invoke(main, ["cache", "--help"])
    assert result.exit_code == 0
    verify(result.output)


def testApiEndToEndApproval(tmp_path):
    contextKey = "d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a"
    filePayload = base64.b64encode(b"hello approval").decode()
    dataPayload = base64.b64encode(b"approval data").decode()

    with _makeClient(tmp_path) as client:
        putFileResponse = client.put(
            "/file",
            json={"contextKey": contextKey, "path": "/approval.txt", "blockData": filePayload},
        )
        fileBlockId = putFileResponse.json()["blockID"]

        getFileResponse = client.get(f"/blocks/{fileBlockId}")
        fileData = base64.b64decode(getFileResponse.json()["blockData"])

        putDataResponse = client.put("/data", json={"blockData": dataPayload})
        dataBlockId = putDataResponse.json()["blockID"]

    app.dependency_overrides.clear()

    snapshot = {
        "putFile": {
            "status": putFileResponse.status_code,
            "blockID": fileBlockId,
        },
        "getFile": {
            "status": getFileResponse.status_code,
            "storedPrefix": fileData[:16].hex(),
            "storedLength": len(fileData),
            "isPaddedToBlockSize": len(fileData) == BlockSize,
        },
        "putData": {
            "status": putDataResponse.status_code,
            "blockID": dataBlockId,
        },
    }

    verify(json.dumps(snapshot, indent=2, sort_keys=True))
