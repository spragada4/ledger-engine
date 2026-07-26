import os

# Must be set BEFORE importing app.database / app.main,
# so the test DB URL is picked up when the engine is created.
os.environ["DATABASE_URL"] = "postgresql://ledger_user:ledger_pass@localhost:5433/ledger_test_db"

import pytest
from sqlalchemy import text

from app.main import app, get_db
from app.database import SessionLocal


@pytest.fixture(autouse=True)
def clean_tables():
    """Runs before and after every test — wipes all tables for a clean slate."""
    db = SessionLocal()
    db.execute(text("TRUNCATE TABLE ledger_entries, transfers, accounts RESTART IDENTITY CASCADE"))
    db.commit()
    db.close()
    yield
    db = SessionLocal()
    db.execute(text("TRUNCATE TABLE ledger_entries, transfers, accounts RESTART IDENTITY CASCADE"))
    db.commit()
    db.close()