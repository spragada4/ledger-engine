import sys
from decimal import Decimal

from app.database import SessionLocal
from app import models
from app.main import get_account_balance


def reconcile():
    db = SessionLocal()

    try:
        entries = db.query(models.LedgerEntry).all()

        total_credits = Decimal("0.00")
        total_debits = Decimal("0.00")

        for entry in entries:
            if entry.direction == "credit":
                total_credits += entry.amount
            elif entry.direction == "debit":
                total_debits += entry.amount

        print("=== System-wide totals ===")
        print(f"Total credits: {total_credits}")
        print(f"Total debits:  {total_debits}")
        print()

        print("=== Per-account balances ===")
        accounts = db.query(models.Account).all()
        for account in accounts:
            balance = get_account_balance(db, account.id)
            print(f"{account.name}: {balance}")
        print()

        print("=== Per-transfer integrity check ===")
        mismatches = check_transfer_integrity(db)
        if mismatches:
            for m in mismatches:
                print(
                    f"Transfer {m['transfer_id']}: expected {m['expected']}, "
                    f"found debit_total={m['debit_total']}, credit_total={m['credit_total']}"
                )
        else:
            print("All transfers match their recorded ledger entries")
        print()

        discrepancy = total_credits - total_debits
        system_balanced = discrepancy == Decimal("0.00")
        transfers_intact = len(mismatches) == 0

        if system_balanced and transfers_intact:
            print("✅ Ledger is balanced")
            sys.exit(0)
        else:
            if not system_balanced:
                print(f"❌ Ledger is UNBALANCED — discrepancy: {discrepancy}")
            if not transfers_intact:
                print(f"❌ {len(mismatches)} transfer(s) failed integrity check")
            sys.exit(1)

    finally:
        db.close()


def check_transfer_integrity(db):
    """
    For every transfer, verify its linked ledger entries still sum to
    exactly the transfer's recorded amount (one debit + one credit,
    both equal to transfer.amount). Catches cases where a ledger entry
    was altered after the fact, even if system-wide totals still balance.
    """
    transfers = db.query(models.Transfer).all()
    mismatches = []

    for transfer in transfers:
        entries = db.query(models.LedgerEntry).filter(
            models.LedgerEntry.transfer_id == transfer.id
        ).all()

        debit_total = sum(e.amount for e in entries if e.direction == "debit")
        credit_total = sum(e.amount for e in entries if e.direction == "credit")

        if debit_total != transfer.amount or credit_total != transfer.amount:
            mismatches.append({
                "transfer_id": transfer.id,
                "expected": transfer.amount,
                "debit_total": debit_total,
                "credit_total": credit_total,
            })

    return mismatches        


if __name__ == "__main__":
    reconcile()