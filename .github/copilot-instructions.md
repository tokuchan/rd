# Copilot Agent Instructions

## Code style and linting

This project uses **black**, **isort**, and **flake8** to enforce consistent formatting and style.
Before opening a pull request, always run these tools and fix any issues they report:

```bash
black --line-length 100 src/ tests/
isort --profile black --line-length 100 src/ tests/
flake8 --max-line-length 100 --extend-ignore E203,W503 src/ tests/
```

The same checks run automatically in CI (`.github/workflows/lint.yml`) on every push and pull
request, so PRs will be blocked if the code is not clean.

## Terminology

### Data-context key pair

Each user owns a **data context** — a namespace that holds their file tree in the BlockCache.
The context is identified by a public/private key pair:

- **`contextKey`** — the *public* part of the key pair. Used as input to `SHA3-256(contextKey ‖ str(path))` when deriving block IDs for file-addressed blocks (`PUT /file`). Encoded as a hex string (e.g. an ED25519 public key).
- **`privateContextKey`** — the *private* part of the key pair. Never transmitted to the server; used client-side to sign or derive capabilities. The algorithm has not yet been finalised; ED25519 is the leading candidate.

Do **not** rename `contextKey` to `publicKey` or any other synonym — the field name is intentional and reflects the domain concept of a "data context", not a generic public-key primitive.
