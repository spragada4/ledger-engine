import uuid
import threading
from decimal import Decimal

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_concurrent_transfers_do_not_overdraft_account():
    # Setup: one funded account, one receiving account
    resp_a = client.post("/accounts", json={"name": "Overdraft-Test-Source"})
    resp_b = client.post("/accounts", json={"name": "Overdraft-Test-Dest"})

    account_a_id = resp_a.json()["id"]
    account_b_id = resp_b.json()["id"]

    client.post(f"/accounts/{account_a_id}/deposit", params={"amount": "100.00"})

    transfer_amount = Decimal("10.00")
    num_requests = 20

    results = []

    def fire_transfer():
        resp = client.post(
            "/transfers",
            json={
                "from_account_id": account_a_id,
                "to_account_id": account_b_id,
                "amount": str(transfer_amount),
            },
            headers={"idempotency-key": str(uuid.uuid4())},
        )
        results.append(resp.status_code)

    threads = [threading.Thread(target=fire_transfer) for _ in range(num_requests)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    successful = [r for r in results if r == 200]
    failed = [r for r in results if r == 400]

    final_balance = Decimal(
        client.get(f"/accounts/{account_a_id}/balance").json()["balance"]
    )

    print(f"\nSuccessful transfers: {len(successful)}")
    print(f"Failed (insufficient funds): {len(failed)}")
    print(f"Final balance: {final_balance}")

    # Only 10 transfers of 10.00 should succeed from a 100.00 balance
    assert len(successful) == 10, f"Expected exactly 10 successful transfers, got {len(successful)}"
    assert final_balance == Decimal("0.00"), f"Expected final balance 0.00, got {final_balance}"