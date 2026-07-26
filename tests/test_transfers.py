from decimal import Decimal
from fastapi.testclient import TestClient

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

    # Step 2: confirm both start at 0.00
    balance_a = client.get(f"/accounts/{account_a_id}/balance")
    balance_b = client.get(f"/accounts/{account_b_id}/balance")

    assert balance_a.status_code == 200
    assert balance_b.status_code == 200
    assert Decimal(balance_a.json()["balance"]) == Decimal("0.00")
    assert Decimal(balance_b.json()["balance"]) == Decimal("0.00")

    # Step 3: transfer from A to B
    transfer_amount = Decimal("50.00")
    transfer_resp = client.post("/transfers", json={
        "from_account_id": account_a_id,
        "to_account_id": account_b_id,
        "amount": str(transfer_amount),
    })

    assert transfer_resp.status_code == 200
    assert transfer_resp.json()["status"] == "completed"

    # Step 4: confirm balances updated correctly
    balance_a_after = client.get(f"/accounts/{account_a_id}/balance")
    balance_b_after = client.get(f"/accounts/{account_b_id}/balance")

    assert Decimal(balance_a_after.json()["balance"]) == -transfer_amount
    assert Decimal(balance_b_after.json()["balance"]) == transfer_amount