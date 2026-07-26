import uuid
from decimal import Decimal

from fastapi import FastAPI, Depends, HTTPException, Header
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models, schemas

app = FastAPI(title="Ledger Engine")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/accounts", response_model=schemas.AccountOut)
def create_account(payload: schemas.AccountCreate, db: Session = Depends(get_db)):
    account = models.Account(name=payload.name)
    db.add(account)
    db.commit()
    db.refresh(account)
    return account

def get_account_balance(db: Session, account_id: uuid.UUID) -> Decimal:
    entries = db.query(models.LedgerEntry).filter(
        models.LedgerEntry.account_id == account_id
    ).all()

    balance = Decimal("0.00")
    for entry in entries:
        if entry.direction == "credit":
            balance += entry.amount
        elif entry.direction == "debit":
            balance -= entry.amount
    return balance


@app.get("/accounts/{account_id}/balance", response_model=schemas.BalanceOut)
def get_balance(account_id: uuid.UUID, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    balance = get_account_balance(db, account_id)
    return schemas.BalanceOut(account_id=account_id, balance=balance)


@app.post("/transfers", response_model=schemas.TransferOut)
def create_transfer(
    payload: schemas.TransferCreate,
    idempotency_key: str = Header(...),
    db: Session = Depends(get_db),
):
    existing = db.query(models.Transfer).filter(
        models.Transfer.idempotency_key == idempotency_key
    ).first()

    if existing:
        if existing.status == "completed":
            return existing
        elif existing.status == "pending":
            raise HTTPException(
                status_code=409,
                detail="Transfer with this idempotency key is already in progress",
            )

    # Lock both accounts in a consistent order (by ID) to prevent deadlocks
    account_ids_sorted = sorted([payload.from_account_id, payload.to_account_id])
    locked_accounts = {}
    for acc_id in account_ids_sorted:
        acc = db.query(models.Account).filter(
            models.Account.id == acc_id
        ).with_for_update().first()
        locked_accounts[acc_id] = acc

    from_account = locked_accounts.get(payload.from_account_id)
    to_account = locked_accounts.get(payload.to_account_id)

    if not from_account or not to_account:
        raise HTTPException(status_code=404, detail="One or both accounts not found")

    if payload.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # --- NEW: sufficient funds check ---
    balance = get_account_balance(db, payload.from_account_id)
    if balance < payload.amount:
        raise HTTPException(status_code=400, detail="Insufficient funds")
    # --- end new code ---

    transfer = models.Transfer(
        idempotency_key=idempotency_key,
        from_account_id=payload.from_account_id,
        to_account_id=payload.to_account_id,
        amount=payload.amount,
        status="pending",
    )
    db.add(transfer)
    db.flush()

    debit_entry = models.LedgerEntry(
        account_id=payload.from_account_id,
        transfer_id=transfer.id,
        direction="debit",
        amount=payload.amount,
    )
    credit_entry = models.LedgerEntry(
        account_id=payload.to_account_id,
        transfer_id=transfer.id,
        direction="credit",
        amount=payload.amount,
    )
    db.add_all([debit_entry, credit_entry])

    transfer.status = "completed"
    db.commit()
    db.refresh(transfer)
    return transfer

@app.post("/accounts/{account_id}/deposit", response_model=schemas.BalanceOut)
def deposit(account_id: uuid.UUID, amount: Decimal, db: Session = Depends(get_db)):
    account = db.query(models.Account).filter(models.Account.id == account_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    if amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    entry = models.LedgerEntry(
        account_id=account_id,
        transfer_id=None,
        direction="credit",
        amount=amount,
    )
    db.add(entry)
    db.commit()

    balance = get_account_balance(db, account_id)
    return schemas.BalanceOut(account_id=account_id, balance=balance)   