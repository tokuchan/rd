# Copilot Agent Instructions

## Terminology

### Data-context key pair

Each user owns a **data context** — a namespace that holds their file tree in the BlockCache.
The context is identified by a public/private key pair:

- **`contextKey`** — the *public* part of the key pair. Used as input to `SHA3-256(contextKey ‖ str(path))` when deriving block IDs for file-addressed blocks (`PUT /file`). Encoded as a hex string (e.g. an ED25519 public key).
- **`privateContextKey`** — the *private* part of the key pair. Never transmitted to the server; used client-side to sign or derive capabilities. The algorithm has not yet been finalised; ED25519 is the leading candidate.

Do **not** rename `contextKey` to `publicKey` or any other synonym — the field name is intentional and reflects the domain concept of a "data context", not a generic public-key primitive.
