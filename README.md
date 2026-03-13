# rd
Code Repository for Reliable Data System

## QUICKSTART
Run the system locally with `uv`:

```bash
uv sync
uv run rd cache --reload
```

The API will be available at `http://127.0.0.1:8000`.
Interactive API docs are available at `http://127.0.0.1:8000/docs` (and `http://127.0.0.1:8000/redoc`).

## BUILDING

### Prerequisites
- Python 3.11+
- `uv` installed

### Install dependencies
```bash
uv sync --all-groups
```

### Run tests
```bash
uv run pytest
```

### Run lint/format checks
```bash
uv run black --line-length 100 src/ tests/
uv run isort --profile black --line-length 100 src/ tests/
uv run flake8 --max-line-length 100 --extend-ignore E203,W503 src/ tests/
```

### Build distributable artifacts
```bash
uv build
```

### Run the server
```bash
uv run rd cache
```

## The Core Principles
These are the core principles of the Reliable Data system:

1. Your data should not have to be tied to any particular storage device or system. 
2. You should be able to access any particular file from any device you own. 
3. If a device is destroyed, you should not lose the data on that device. 
4. It should be easy to rent out storage you own; or rent storage from others, which you tie into your context. 
5. The system should be open source, open protocol, and open format. That way, you can always take it with you. 

## Architecture — Port & Adaptor Pattern

The block-cache layer uses the **Port & Adaptor** (Hexagonal Architecture) pattern, inspired by
the [Arjancodes YouTube series on Ports & Adaptors](https://www.youtube.com/c/ArjanCodes).

### Directory layout

```
src/rd/
├── BlockCache/               # Domain package (ports, models, use-case logic)
│   ├── __init__.py
│   ├── errors.py             # Domain-specific exceptions
│   ├── models.py             # Key and Block dataclasses
│   ├── ports.py              # BlockCachePort Protocol
│   └── useCases.py           # Pure application logic (key derivation, store helpers)
├── adaptors/                 # Concrete back-end implementations
│   ├── __init__.py
│   ├── sqliteBlockCache.py   # SQLite adaptor (default, used by the REST server)
│   ├── dbmBlockCache.py      # DBM adaptor (built-in Python dbm module)
│   └── fsBlockCache.py       # Filesystem adaptor (one file per block)
├── main.py                   # FastAPI application (uses SqliteBlockCache + useCases)
├── cli.py                    # Click CLI entry point
└── …
```

### Domain layer (`src/rd/BlockCache/`)

| Module | Purpose |
|---|---|
| `errors.py` | `BlockNotFoundError`, `BlockTooLargeError` |
| `models.py` | `Key` (frozen dataclass, string value) and `Block` (bytes + `pad()` helper).  `BLOCK_SIZE = 4096`. |
| `ports.py` | `BlockCachePort` — a `typing.Protocol` with exactly three methods: `store(key, block) → Block`, `get(key) → Block \| None`, and `delete(key) → bool`. |
| `useCases.py` | `derive_file_block_key`, `derive_data_block_key`, `store_file_block`, `store_data_block` — pure functions that work with any `BlockCachePort` adaptor. |

#### `BlockCachePort` Protocol

```python
class BlockCachePort(Protocol):
    def store(self, key: Key, block: Block) -> Block: ...
    def get(self, key: Key) -> Block | None: ...
    def delete(self, key: Key) -> bool: ...
```

Any class that implements these three methods satisfies the protocol via structural sub-typing —
no inheritance required.

### Key derivation (`useCases.py`)

| Function | Key formula |
|---|---|
| `derive_file_block_key(context_key, path)` | `SHA3-256(bytes.fromhex(context_key) ‖ str(path).encode())` |
| `derive_data_block_key(block)` | `SHA3-256(block.data)` |

`context_key` is the *public* part of the owner's **data-context key pair** — a hex-encoded
ED25519 public key that acts as a namespace for all of a user's file-addressed blocks.

### Adaptors (`src/rd/adaptors/`)

| Adaptor | Back-end | Notes |
|---|---|---|
| `SqliteBlockCache` | SQLAlchemy + SQLite | Default for the REST server; creates its own `block_cache` table. |
| `DbmBlockCache` | Python built-in `dbm` | Portable, no extra dependencies; file path passed to constructor. |
| `FsBlockCache` | Plain filesystem | One file per block; key is used as filename (percent-encoded for safety). |

All three adaptors implement the full `BlockCachePort` interface: `store`, `get`, and `delete`.

### Adding a new adaptor

1. Create `src/rd/adaptors/myBackend.py`.
2. Define a class with:
   - `store(self, key: Key, block: Block) -> Block`
   - `get(self, key: Key) -> Block | None`
   - `delete(self, key: Key) -> bool`
3. Pass an instance of your adaptor wherever a `BlockCachePort` is expected.

No base class or registration step is required — Python's structural sub-typing
(`typing.Protocol`) handles the rest.

 