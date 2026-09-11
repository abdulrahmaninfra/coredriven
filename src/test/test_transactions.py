"""Cash-counter tests: recharge, deduct, and the transactions ledger.

Covers:

- permissions: only admins move balances AND only admins read the ledger
- ledger math: signed amounts, balance_after snapshots, new_balance in responses
- overdraft: deductions beyond the balance are rejected with no side effects
- scoping: the per-user ledger endpoint returns only that user's rows
- the full counter loop: a zero-balance customer recharges, then starts a session
"""

import os
import tempfile

_tmp_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_NAME"] = _tmp_db
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["PASSWORD_HASH_SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient

from main import app
from src.database.customers.create import CreateNewUser
from src.database.customers.database import SessionLocal
from src.database.customers.read import GetUser
from src.database.transactions.models import Transactions

# NOTE: names use the "txn_" prefix so they cannot collide with the other
# test modules sharing one database file (get_settings() is lru_cached).

BASE = "/transactions"


def _ensure_admin(client):
    db = SessionLocal()
    try:
        if GetUser(db).get_user_by_username("txn_admin") is None:
            CreateNewUser("txn_admin", "secret123", "555-txn_admin", 50.0).create_user(db)
        admin = GetUser(db).get_user_by_username("txn_admin")
        admin.is_admin = True
        admin.is_superadmin = True
        db.commit()
    finally:
        db.close()
    return _login(client, "txn_admin")


def _login(client, username, password="secret123"):
    response = client.post("/auth/login", data={"username": username, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _register(client, admin_headers, username):
    response = client.post(
        "/users",
        json={"username": username, "password": "secret123", "phone_number": f"555-{username}"},
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _recharge(client, admin_headers, username, amount, note=None):
    payload = {"target_username": username, "amount": amount}
    if note is not None:
        payload["note"] = note
    return client.post(f"{BASE}/recharge", json=payload, headers=admin_headers)


def _deduct(client, admin_headers, username, amount, note=None):
    payload = {"target_username": username, "amount": amount}
    if note is not None:
        payload["note"] = note
    return client.post(f"{BASE}/deduct", json=payload, headers=admin_headers)


def _balance_of(client, username, password="secret123"):
    return client.get("/auth/me", headers=_login(client, username, password)).json()["balance"]


def test_recharge_adds_balance_and_writes_ledger():
    with TestClient(app) as client:
        admin = _ensure_admin(client)
        _register(client, admin, "txn_alice")

        response = _recharge(client, admin, "txn_alice", 50.25, note="cash at counter")
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["username"] == "txn_alice"
        assert body["new_balance"] == 50.25
        assert body["transaction"]["amount"] == 50.25
        assert body["transaction"]["balance_after"] == 50.25
        assert body["transaction"]["note"] == "cash at counter"

        # The balance is real: the customer sees it on /auth/me.
        assert _balance_of(client, "txn_alice") == 50.25

        # Second recharge stacks on top of the first.
        response = _recharge(client, admin, "txn_alice", 9.75)
        assert response.json()["new_balance"] == 60.0


def test_only_admin_can_move_balances():
    with TestClient(app) as client:
        admin = _ensure_admin(client)
        _register(client, admin, "txn_mallory")
        customer = _login(client, "txn_mallory")

        # Anonymous -> 401
        assert client.post(
            f"{BASE}/recharge", json={"target_username": "txn_mallory", "amount": 5}
        ).status_code == 401

        # Customer -> 403 on both operations
        assert client.post(
            f"{BASE}/recharge",
            json={"target_username": "txn_mallory", "amount": 5},
            headers=customer,
        ).status_code == 403
        assert client.post(
            f"{BASE}/deduct",
            json={"target_username": "txn_mallory", "amount": 5},
            headers=customer,
        ).status_code == 403


def test_recharge_validates_amount_and_target():
    with TestClient(app) as client:
        admin = _ensure_admin(client)

        # Zero and negative amounts -> 422
        assert _recharge(client, admin, "txn_admin", 0).status_code == 422
        assert _recharge(client, admin, "txn_admin", -10).status_code == 422

        # Unknown target -> 404
        assert _recharge(client, admin, "txn_ghost", 10).status_code == 404


def test_deduct_reduces_balance_and_records_negative():
    with TestClient(app) as client:
        admin = _ensure_admin(client)
        _register(client, admin, "txn_bob")
        _recharge(client, admin, "txn_bob", 40.0)

        response = _deduct(client, admin, "txn_bob", 15.5, note="correction")
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["transaction"]["amount"] == -15.5
        assert body["new_balance"] == 24.5
        assert _balance_of(client, "txn_bob") == 24.5


def test_deduct_overdraft_rejected_without_side_effects():
    with TestClient(app) as client:
        admin = _ensure_admin(client)
        _register(client, admin, "txn_carol")
        _recharge(client, admin, "txn_carol", 10.0)

        response = _deduct(client, admin, "txn_carol", 10.01)
        assert response.status_code == 400, response.text

        # Nothing moved: balance intact, no orphan ledger row.
        assert _balance_of(client, "txn_carol") == 10.0
        with SessionLocal() as db:
            user = GetUser(db).get_user_by_username("txn_carol")
            rows = db.query(Transactions).filter(Transactions.user_id == user.id).all()
            assert len(rows) == 1  # only the original recharge
            assert float(rows[0].amount) == 10.0


def test_ledger_admin_only_scoping():
    with TestClient(app) as client:
        admin = _ensure_admin(client)
        _register(client, admin, "txn_dan")
        _register(client, admin, "txn_eve")
        _recharge(client, admin, "txn_dan", 10.0)
        _recharge(client, admin, "txn_eve", 20.0)

        # Admin sees both users' rows.
        rows = client.get(BASE, headers=admin).json()
        usernames = {row["username"] for row in rows}
        assert {"txn_dan", "txn_eve"} <= usernames

        # Customers cannot read the ledger at all (admin-only).
        assert client.get(BASE, headers=_login(client, "txn_dan")).status_code == 403

        # Anonymous -> 401
        assert client.get(BASE).status_code == 401

        # The per-user filter returns only that user's rows.
        dan_rows = client.get(f"{BASE}?username=txn_dan", headers=admin).json()
        assert all(row["username"] == "txn_dan" for row in dan_rows)
        assert any(row["amount"] == 10.0 for row in dan_rows)

        # Unknown username -> empty list, not an error.
        assert client.get(f"{BASE}?username=no-such-user", headers=admin).json() == []


def test_recharge_enables_session_start():
    with TestClient(app) as client:
        admin = _ensure_admin(client)
        _register(client, admin, "txn_frank")

        # A workstation to log into.
        ws = client.post(
            "/workstations",
            json={"name": "txn-ws-1", "hourly_rate": 10.0},
            headers=admin,
        )
        assert ws.status_code == 201, ws.text
        workstation_id = ws.json()["id"]

        # Zero balance: login on the machine is refused.
        frank = _login(client, "txn_frank")
        response = client.post("/sessions", json={"workstation_id": workstation_id}, headers=frank)
        assert response.status_code == 400, response.text

        # Cash counter fixes it: recharge, then the session starts.
        assert _recharge(client, admin, "txn_frank", 20.0).status_code == 201
        response = client.post("/sessions", json={"workstation_id": workstation_id}, headers=frank)
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "active"