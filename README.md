# Ledger Engine

An idempotent, double-entry payments ledger service built with FastAPI, SQLAlchemy, and PostgreSQL — built to demonstrate correct handling of the hard problems in real payment systems: safe request retries, concurrency-safe balance updates, and an auditable transaction history.

**Status:** Feature-complete for local/demo use (Docker Compose). Not currently deployed.

---

## Why this project

Most CRUD apps don't have to think about money moving twice, two requests racing on the same account, or how to prove a ledger is internally consistent after the fact. This project builds a small transaction engine from scratch to work through exactly those problems — the same class of problem underlying real systems like Stripe's Payments API.

---

## Core design decisions

- **No stored balance column.** Every account's balance is *derived* — computed by summing its ledger entries (`sum(credits) - sum(debits)`) rather than stored and mutated. This makes the ledger an immutable, append-only audit trail: there's only one source of truth (transaction history), so it can never silently drift out of sync with itself.
- **`Numeric(18,2)` for all monetary amounts**, never `Float` — avoids binary floating-point rounding errors accumulating across transactions.
- **Idempotency keys, not just idempotent design.** Clients supply an `Idempotency-Key` header on every transfer. Duplicate requests (e.g. from a client retry after a timeout) return the original result instead of double-processing.
- **Row-level locking with deadlock-safe ordering.** Concurrent transfers on the same account are serialized using `SELECT ... FOR UPDATE`, with accounts always locked in a consistent (UUID-sorted) order regardless of transfer direction — preventing classic circular-wait deadlocks.
- **Reconciliation as a first-class concern, not an afterthought.** System-wide totals balancing is *not* sufficient proof the ledger is correct — see below.

---
## Architecture

```mermaid
flowchart LR
    Client["Client<br/>(curl / Swagger UI)"]
    App["FastAPI App<br/>(app container)"]
    DB[("PostgreSQL<br/>dev db")]
    TestDB[("PostgreSQL<br/>test db · isolated")]
    Reconcile["reconcile.py<br/>(standalone integrity check)"]
    CI["GitHub Actions CI<br/>(pytest + migrations)"]

    Client -->|HTTP requests| App
    App -->|reads/writes| DB
    Reconcile -->|verifies| DB
    CI -->|runs tests against| TestDB

    style Client fill:#e8f0fe,stroke:#4285f4
    style App fill:#e6f4ea,stroke:#34a853
    style DB fill:#fef7e0,stroke:#fbbc04
    style TestDB fill:#fef7e0,stroke:#fbbc04
    style Reconcile fill:#fce8e6,stroke:#ea4335
    style CI fill:#f3e8fd,stroke:#a142f4
```

**Key point:** the test database (`test_db`, port `5433`) is a completely separate Postgres instance from the dev database (`db`, port `5432`). No test run ever touches dev data, and vice versa — this isolation is what made the concurrency and idempotency tests trustworthy.

---

## What's built

### Data model
`accounts`, `transfers`, `ledger_entries` — see `app/models.py`. Alembic migrations tracked from day one, including a fix where a Python-side default (`default=0`) was caught *not* enforcing at the database level, and corrected with `server_default`.

### API (`app/main.py`)
- `POST /accounts` — create an account
- `GET /accounts/{id}/balance` — computed balance from ledger history
- `POST /accounts/{id}/deposit` — fund an account (dev/testing convenience)
- `POST /transfers` — double-entry transfer between accounts, with idempotency handling, sufficient-funds checks, and row-level locking

### Tests (`tests/`)
Isolated test database with automatic table truncation between every test.
- `test_transfer_updates_balances_correctly` — basic transfer correctness
- `test_duplicate_transfer_with_same_idempotency_key_is_not_double_processed` — proves retried requests don't double-charge
- `test_concurrent_transfers_do_not_overdraft_account` — fires 20 concurrent transfers against one account:
  - **Before the locking fix:** 15/20 succeeded (should have been 10) — a real, reproduced race condition
  - **After the fix:** exactly 10/20 succeed, balance lands at exactly `0.00`

### Reconciliation (`reconcile.py`)
- System-wide check: total credits must equal total debits
- Per-account balance breakdown
- Per-transfer integrity check — added after a manual data edit shifted `5.00` between two accounts' credit entries while leaving system-wide totals balanced. This is documented deliberately: **global totals balancing alone does not prove ledger correctness**, since amounts can be misattributed between accounts without changing the system-wide sum.
- Exit code `0` if fully balanced, `1` otherwise (CI/monitoring-friendly)

### CI/CD
GitHub Actions runs the full test suite (including the concurrency test) on every push — spins up an ephemeral Postgres service, applies migrations, runs pytest.

### Containerization
Full stack (`app`, `db`, `test_db`) runs via a single `docker compose up -d --build`.

---

## Tech stack
Python · FastAPI · SQLAlchemy · Alembic · PostgreSQL · pytest · Docker · GitHub Actions

---

## Running it locally

```bash
# start the full stack (app + dev db + test db)
docker compose up -d --build

# apply migrations (dev db)
alembic upgrade head

# apply migrations (test db)
DATABASE_URL="postgresql://ledger_user:ledger_pass@localhost:5433/ledger_test_db" alembic upgrade head

# API docs
open http://localhost:8000/docs

# run tests
pytest tests/ -v

# run the reconciliation check
python reconcile.py
```

---

## Known limitations / future work
- Not currently deployed to a public host — runs via Docker Compose locally or in CI
- No authentication/authorization on the API (out of scope for this project's focus on transaction correctness)
- Reconciliation is run manually/on-demand, not scheduled
- No support for partial/multi-currency transfers