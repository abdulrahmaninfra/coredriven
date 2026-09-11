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

# NOTE: "prm_" prefix avoids rows colliding with the other test modules:
# get_settings() is lru_cached, so all modules share one database file.


def _seed_superadmin(username):
    db = SessionLocal()
    try:
        if GetUser(db).get_user_by_username(username) is None:
            CreateNewUser(username, "secret123", f"555-{username}", 50.0).create_user(
                db
            )
        admin = GetUser(db).get_user_by_username(username)
        admin.is_admin = True
        admin.is_superadmin = True
        db.commit()
    finally:
        db.close()


def _login(client, username, password="secret123"):
    response = client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _super_headers(client):
    _seed_superadmin("prm_super")
    return _headers(_login(client, "prm_super"))


def _make_user(client, super_headers, username):
    response = client.post(
        "/users",
        json={
            "username": username,
            "password": "secret123",
            "phone_number": f"555-{username}",
            "balance": 0.0,
        },
        headers=super_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _grant(client, super_headers, username, payload):
    response = client.put(
        f"/users/{username}/admin", json=payload, headers=super_headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def _sub_headers(client, super_headers, username, payload):
    _make_user(client, super_headers, username)
    _grant(client, super_headers, username, payload)
    return _headers(_login(client, username))


def test_user_manager_is_scoped_to_users():
    with TestClient(app) as client:
        super_headers = _super_headers(client)
        sub = _sub_headers(
            client,
            super_headers,
            "prm_users_only",
            {"is_admin": True, "permissions": {"can_manage_users": True}},
        )

        # Allowed: user management.
        response = client.post(
            "/users",
            json={
                "username": "prm_users_target",
                "password": "secret123",
                "phone_number": "555-prm-target",
                "balance": 0.0,
            },
            headers=sub,
        )
        assert response.status_code == 201, response.text
        assert client.get("/users", headers=sub).status_code == 200

        # Denied: workstations, billing writes and billing reads.
        assert (
            client.post(
                "/workstations",
                json={"name": "prm-ws-denied", "hourly_rate": 5.0},
                headers=sub,
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/transactions/recharge",
                json={"target_username": "prm_users_target", "amount": 5.0},
                headers=sub,
            ).status_code
            == 403
        )
        assert client.get("/transactions", headers=sub).status_code == 403


def test_read_only_billing_can_list_but_not_move():
    with TestClient(app) as client:
        super_headers = _super_headers(client)
        sub = _sub_headers(
            client,
            super_headers,
            "prm_billing_ro",
            {"is_admin": True, "permissions": {"read_only_billing": True}},
        )

        assert client.get("/transactions", headers=sub).status_code == 200
        assert (
            client.post(
                "/transactions/recharge",
                json={"target_username": "prm_super", "amount": 5.0},
                headers=sub,
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/transactions/deduct",
                json={"target_username": "prm_super", "amount": 5.0},
                headers=sub,
            ).status_code
            == 403
        )


def test_billing_manager_can_move_and_list():
    with TestClient(app) as client:
        super_headers = _super_headers(client)
        target = _make_user(client, super_headers, "prm_billing_target")
        assert target["balance"] == 0.0
        sub = _sub_headers(
            client,
            super_headers,
            "prm_billing_rw",
            {"is_admin": True, "permissions": {"can_manage_billing": True}},
        )

        response = client.post(
            "/transactions/recharge",
            json={"target_username": "prm_billing_target", "amount": 25.0},
            headers=sub,
        )
        assert response.status_code == 201, response.text
        assert response.json()["new_balance"] == 25.0
        assert client.get("/transactions", headers=sub).status_code == 200


def test_workstation_manager_cannot_manage_users():
    with TestClient(app) as client:
        super_headers = _super_headers(client)
        sub = _sub_headers(
            client,
            super_headers,
            "prm_ws_only",
            {"is_admin": True, "permissions": {"can_manage_workstations": True}},
        )

        response = client.post(
            "/workstations",
            json={"name": "prm-ws-allowed", "hourly_rate": 5.0},
            headers=sub,
        )
        assert response.status_code == 201, response.text
        assert (
            client.post(
                "/users",
                json={
                    "username": "prm_ws_nouser",
                    "password": "secret123",
                    "phone_number": "555-prm-nouser",
                    "balance": 0.0,
                },
                headers=sub,
            ).status_code
            == 403
        )


def test_admin_manager_cannot_escalate_without_superadmin():
    with TestClient(app) as client:
        super_headers = _super_headers(client)
        sub = _sub_headers(
            client,
            super_headers,
            "prm_admins_limited",
            {"is_admin": True, "permissions": {"can_manage_admins": True}},
        )
        _make_user(client, super_headers, "prm_escalation_target")

        # Cannot grant superadmin or can_manage_admins.
        assert (
            client.put(
                "/users/prm_escalation_target/admin",
                json={"is_superadmin": True},
                headers=sub,
            ).status_code
            == 403
        )
        assert (
            client.put(
                "/users/prm_escalation_target/admin",
                json={
                    "is_admin": True,
                    "permissions": {"can_manage_admins": True},
                },
                headers=sub,
            ).status_code
            == 403
        )
        # Cannot touch the superadmin either.
        assert (
            client.put(
                "/users/prm_super/admin",
                json={"is_admin": False},
                headers=sub,
            ).status_code
            == 403
        )

        # Can grant ordinary flags and read permissions.
        response = client.put(
            "/users/prm_escalation_target/admin",
            json={"is_admin": True, "permissions": {"can_manage_users": True}},
            headers=sub,
        )
        assert response.status_code == 200, response.text
        assert (
            client.get(
                "/users/prm_escalation_target/permissions", headers=sub
            ).status_code
            == 200
        )


def test_any_manage_flag_covers_other_users_sessions():
    with TestClient(app) as client:
        super_headers = _super_headers(client)
        player = _make_user(client, super_headers, "prm_player")
        response = client.put(
            "/users/prm_player", json={"balance": 50.0}, headers=super_headers
        )
        assert response.status_code == 200, response.text

        ws = client.post(
            "/workstations",
            json={"name": "prm-ws-sess", "hourly_rate": 5.0},
            headers=super_headers,
        )
        assert ws.status_code == 201, ws.text

        started = client.post(
            "/sessions",
            json={"workstation_id": ws.json()["id"]},
            headers=_headers(_login(client, "prm_player")),
        )
        assert started.status_code == 201, started.text
        session_id = started.json()["id"]

        # Sub-admin with no flags stays scoped to their own sessions.
        _make_user(client, super_headers, "prm_noflag")
        _grant(client, super_headers, "prm_noflag", {"is_admin": True})
        noflag = _headers(_login(client, "prm_noflag"))
        assert (
            client.get(f"/sessions/{session_id}", headers=noflag).status_code == 403
        )

        # Sub-admin with a manage flag can view and list it.
        sub = _sub_headers(
            client,
            super_headers,
            "prm_sess_viewer",
            {"is_admin": True, "permissions": {"can_manage_users": True}},
        )
        response = client.get(f"/sessions/{session_id}", headers=sub)
        assert response.status_code == 200, response.text
        response = client.get(f"/sessions?user_id={player['id']}", headers=sub)
        assert response.status_code == 200, response.text
        assert any(row["id"] == session_id for row in response.json())
