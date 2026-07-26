# Ledger Engine

An idempotent, double-entry payments ledger service built with FastAPI, SQLAlchemy, and PostgreSQL — designed to demonstrate correct handling of the hard problems in real payment systems: safe request retries, concurrency-safe balance updates, and an auditable transaction history.

**Status:** In progress (Phase 4 of 7 complete)

---

## Why this project

Most CRUD apps don't have to think about money moving twice, two requests racing on the same account, or how to prove a ledger is internally consistent after the fact. This project builds a small transaction engine from scratch to work through exactly those problems — the same class of problem underlying real systems like Stripe's Payments API.

---

## Core design decisions

- **No stored balance column.** Every account's balance is *derived* — computed by summing its ledger entries (`sum(credits) - sum(debits)`) rather than stored and mutated. This makes the ledger an immutable, append-only audit trail: there's only one source of truth (transaction history), so it can never silently drift out of sync with itself.
- **`Numeric(18,2)` for all monetary amounts**, never `Float` — avoids binary floating-point rounding errors accumulating across transactions.
- **Idempotency keys, not just idempotent design.** Clients supply an `Idempotency-Key` header on every transfer. Duplicate requests (e.g. from a client retry after a timeout) return the original result instead of double-processing.
- **Row-level locking with deadlock-safe ordering.** Concurrent transfers on the same account are serialized using `SELECT ... FOR UPDATE`, with accounts always locked in a consistent (UUID-sorted) order regardless of transfer direction — preventing classic circular-wait deadlocks.

---

## What's built so far

### Data model
- `accounts`, `transfers`, `ledger_entries` — see `app/models.py`
- Alembic migrations tracked from day one, including a fix where a Python-side default (`default=0`) was caught *not* enforcing at the database level, and corrected with `server_default`

### API (`app/main.py`)
- `POST /accounts` — create an account
- `GET /accounts/{id}/balance` — computed balance from ledger history
- `POST /accounts/{id}/deposit` — fund an account (dev/testing convenience)
- `POST /transfers` — double-entry transfer between accounts, with:
  - Idempotency key handling (duplicate-safe)
  - Sufficient-funds check (rejects overdraft)
  - Row-level locking to prevent race conditions under concurrent load

### Tests (`tests/`)
- Isolated test database (separate Postgres container, port `5433`) with automatic table truncation before/after every test — no shared state between runs
- `test_transfer_updates_balances_correctly` — basic transfer correctness
- `test_duplicate_transfer_with_same_idempotency_key_is_not_double_processed` — proves retried requests don't double-charge
- `test_concurrent_transfers_do_not_overdraft_account` — fires 20 concurrent transfer requests against a single funded account:
  - **Before locking fix:** 15/20 succeeded (should have been 10), draining the account past zero — a real, reproduced race condition
  - **After fix:** exactly 10/20 succeed, final balance lands at exactly `0.00`

---

## Tech stack
Python · FastAPI · SQLAlchemy · Alembic · PostgreSQL · pytest · Docker

---

## Running it locally

```bash
# start dev + test databases
docker compose up -d

# apply migrations (dev db)
alembic upgrade head

# apply migrations (test db)
DATABASE_URL="postgresql://ledger_user:ledger_pass@localhost:5433/ledger_test_db" alembic upgrade head

# run the API
uvicorn app.main:app --reload

# run tests
pytest tests/ -v
```

---

## Coming next
- **Reconciliation script** — standalone check verifying system-wide debits equal credits, plus per-account balance audit
- **Dockerize the app + GitHub Actions CI** — tests running automatically on every push
- **Deployment** — hosted instance + architecture diagram