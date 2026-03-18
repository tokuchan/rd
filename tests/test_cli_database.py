"""Coverage-focused tests for CLI and database helper paths."""

from click.testing import CliRunner

import rd.cli as cli
import rd.database as database


def testDisplayHostWildcardIPv4():
    assert cli._displayHost("0.0.0.0") == "127.0.0.1"


def testDisplayHostWildcardIPv6():
    assert cli._displayHost("::") == "127.0.0.1"


def testDisplayHostPassthrough():
    assert cli._displayHost("127.0.0.2") == "127.0.0.2"


def testConfigureLoggingClampToDebug(monkeypatch):
    captured = {}

    def fakeBasicConfig(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli.logging, "basicConfig", fakeBasicConfig)
    cli._configureLogging(999)
    assert captured["level"] == cli.logging.DEBUG


def testConfigureLoggingClampToCritical(monkeypatch):
    captured = {}

    def fakeBasicConfig(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(cli.logging, "basicConfig", fakeBasicConfig)
    cli._configureLogging(-999)
    assert captured["level"] == cli.logging.CRITICAL


def testCacheCommandInvokesUvicorn(monkeypatch):
    captured = {}

    def fakeRun(appPath, host, port, reload):
        captured["appPath"] = appPath
        captured["host"] = host
        captured["port"] = port
        captured["reload"] = reload

    monkeypatch.setattr(cli.uvicorn, "run", fakeRun)
    runner = CliRunner()
    result = runner.invoke(cli.main, ["cache", "--host", "0.0.0.0", "--port", "9000", "--reload"])

    assert result.exit_code == 0
    assert captured == {
        "appPath": "rd.main:app",
        "host": "0.0.0.0",
        "port": 9000,
        "reload": True,
    }


def testEnableWalExecutesPragma():
    class FakeConnection:
        def __init__(self):
            self.queries = []

        def execute(self, query):
            self.queries.append(query)

    fakeConnection = FakeConnection()
    database._enableWal(fakeConnection, None)
    assert fakeConnection.queries == ["PRAGMA journal_mode=WAL"]


def testInitDbInvokesCreateAll(monkeypatch):
    captured = {}

    def fakeCreateAll(bind):
        captured["bind"] = bind

    monkeypatch.setattr(database.Base.metadata, "create_all", fakeCreateAll)
    database.initDb()
    assert captured["bind"] is database.engine


def testGetDbYieldsAndClosesSession(monkeypatch):
    class FakeSession:
        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    fakeSession = FakeSession()
    monkeypatch.setattr(database, "SessionLocal", lambda: fakeSession)

    generator = database.getDb()
    yielded = next(generator)
    assert yielded is fakeSession
    assert fakeSession.closed is False

    try:
        next(generator)
    except StopIteration:
        pass

    assert fakeSession.closed is True
