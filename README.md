# Ledger Engine

An idempotent, double-entry payments ledger service built with FastAPI, SQLAlchemy, and PostgreSQL.

**Status:** Work in progress.

## Why this project
Demonstrates handling of the core hard problems in payment systems:
- Idempotent transfers (safe request retries)
- Concurrency-safe balance updates
- Double-entry bookkeeping with an immutable ledger
- Reconciliation to detect drift

More details coming as the project develops.
