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

 