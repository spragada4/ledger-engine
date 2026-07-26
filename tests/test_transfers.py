from decimal import Decimal
from fastapi.testclient import TestClient
import uuid

from app.main import app

client = TestClient(app)


def test_transfer_updates_balances_correctly():
    # Step 1: create two accounts
    resp_a = client.post("/accounts", json={"name": "Alice"})
    resp_b = client.post("/accounts", json={"name": "Bob"})

    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    account_a_id = resp_a.json()["id"]
    account_b_id = resp_b.json()["id"]

    client.post(f"/accounts/{account_a_id}/deposit", params={"amount": "1000.00"})

    # Step 2: confirm both start at 0.00
    balance_a = client.get(f"/accounts/{account_a_id}/balance")
    balance_b = client.get(f"/accounts/{account_b_id}/balance")

    assert balance_a.status_code == 200
    assert balance_b.status_code == 200
    assert Decimal(balance_a.json()["balance"]) == Decimal("1000.00")
    assert Decimal(balance_b.json()["balance"]) == Decimal("0.00")

    # Step 3: transfer from A to B
    transfer_amount = Decimal("50.00")
    transfer_resp = client.post(
        "/transfers",
        json={
            "from_account_id": account_a_id,
            "to_account_id": account_b_id,
            "amount": str(transfer_amount),
        },
        headers={"idempotency-key": str(uuid.uuid4())},
    )

    assert transfer_resp.status_code == 200
    assert transfer_resp.json()["status"] == "completed"

    # Step 4: confirm balances updated correctly
    balance_a_after = client.get(f"/accounts/{account_a_id}/balance")
    balance_b_after = client.get(f"/accounts/{account_b_id}/balance")

    assert Decimal(balance_a_after.json()["balance"]) == Decimal("1000.00") - transfer_amount
    assert Decimal(balance_b_after.json()["balance"]) == transfer_amount

def test_duplicate_transfer_with_same_idempotency_key_is_not_double_processed():
    # Create two accounts
    resp_a = client.post("/accounts", json={"name": "Charlie"})
    resp_b = client.post("/accounts", json={"name": "Dana"})

    account_a_id = resp_a.json()["id"]
    account_b_id = resp_b.json()["id"]

    client.post(f"/accounts/{account_a_id}/deposit", params={"amount": "1000.00"})

    idempotency_key = str(uuid.uuid4())
    transfer_amount = Decimal("30.00")

    payload = {
        "from_account_id": account_a_id,
        "to_account_id": account_b_id,
        "amount": str(transfer_amount),
    }
    headers = {"idempotency-key": idempotency_key}

    # Fire the same request twice
    first_resp = client.post("/transfers", json=payload, headers=headers)
    second_resp = client.post("/transfers", json=payload, headers=headers)

    assert first_resp.status_code == 200
    assert second_resp.status_code == 200

    # Both responses should refer to the SAME transfer
    assert first_resp.json()["id"] == second_resp.json()["id"]

    # Balance should reflect ONE transfer, not two
    balance_b = client.get(f"/accounts/{account_b_id}/balance")
    assert Decimal(balance_b.json()["balance"]) == transfer_amount    