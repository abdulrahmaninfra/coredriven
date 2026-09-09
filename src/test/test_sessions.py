import os
import tempfile
from datetime import datetime, timedelta

os.environ["DATABASE_NAME"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["PASSWORD_HASH_SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient

from main import app
from src.database.customers.create import CreateNewUser
from src.database.customers.database import SessionLocal
from src.database.customers.read import GetUser
from src.database.workstations.models import Workstation

# NOTE: usernames / workstation names use the "sess_" prefix so they cannot
# collide with the other test modules: both modules share one database
# file because get_settings() is lru_cached on first import.
# Users are created by an admin (public registration no longer exists) and
# topped up to a working balance the same way.


def _register(client, username, balance=50.0):
    admin_headers = _ensure_admin(client)
    response = client.post(
        "/auth/admin/register",
        json={
            "username": username,
            "password": "secret123",
            "phone_number": f"555-{username}",
            "balance": balance,  # ignored: new users start at 0 until topped up
        },
        headers=admin_headers,
    )
    assert response.status_code == 201, response.text
    if balance:
        response = client.put(
            "/auth/admin/update",
            json={"target_username": username, "balance": balance},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
    return response.json()


def _ensure_admin(client):
    db = SessionLocal()
    try:
        if GetUser(db).get_user_by_username("sess_admin") is None:
            CreateNewUser(
                "sess_admin", "secret123", "555-sess_admin", 50.0
            ).create_user(db)
        GetUser(db).get_user_by_username("sess_admin").is_admin = True
        db.commit()
    finally:
        db.close()
    return _auth_headers(_login(client, "sess_admin"))


def _login(client, username):
    response = client.post(
        "/auth/login", data={"username": username, "password": "secret123"}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth_headers(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_workstation(name, hourly_rate=10.0):
    db = SessionLocal()
    try:
        ws = Workstation(
            id=f"ws-{name}",
            name=name,
            status="available",
            hourly_rate=hourly_rate,
            is_active=True,
        )
        db.add(ws)
        db.commit()
        return ws.id
    finally:
        db.close()


def _user_id(username):
    db = SessionLocal()
    try:
        return GetUser(db).get_user_by_username(username).id
    finally:
        db.close()


def test_start_and_logout_ends_session():
    with TestClient(app) as client:
        _register(client, "sess_u1")
        token = _login(client, "sess_u1")
        headers = _auth_headers(token)
        ws_id = _seed_workstation("sess-ws-1")

        response = client.post(
            "/sessions/start", json={"workstation_id": ws_id}, headers=headers
        )
        assert response.status_code == 201, response.text
        assert response.json()["status"] == "active"
        assert response.json()["cost"] is None

        response = client.post("/auth/logout", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["ended"] is True
        assert body["session"]["status"] == "ended"
        assert body["session"]["cost"] is not None
        assert body["session"]["cost"] >= 0

        # Workstation is freed and balance never went negative.
        response = client.get("/workstations", headers=headers)
        assert response.status_code == 200
        by_id = {ws["id"]: ws for ws in response.json()}
        assert by_id[ws_id]["status"] == "available"

        response = client.get("/auth/users/me", headers=headers)
        assert response.status_code == 200
        assert response.json()["balance"] >= 0

        # Idempotent: second logout reports no active session.
        response = client.post("/auth/logout", headers=headers)
        assert response.status_code == 200
        assert response.json()["ended"] is False


def test_cannot_end_or_read_other_users_session():
    with TestClient(app) as client:
        _register(client, "sess_u2")
        _register(client, "sess_u3")
        token2 = _login(client, "sess_u2")
        token3 = _login(client, "sess_u3")
        ws_id = _seed_workstation("sess-ws-2")

        session_id = (
            client.post(
                "/sessions/start",
                json={"workstation_id": ws_id},
                headers=_auth_headers(token2),
            )
            .json()["id"]
        )

        response = client.post(
            f"/sessions/{session_id}/end", headers=_auth_headers(token3)
        )
        assert response.status_code == 403, response.text

        response = client.get(
            f"/sessions/{session_id}", headers=_auth_headers(token3)
        )
        assert response.status_code == 403, response.text

        # Listing is forced to self: no rows for u3, and filtering by
        # someone else's user_id is forbidden.
        response = client.get("/sessions", headers=_auth_headers(token3))
        assert response.status_code == 200
        assert response.json() == []

        response = client.get(
            f"/sessions?user_id={_user_id('sess_u2')}",
            headers=_auth_headers(token3),
        )
        assert response.status_code == 403, response.text

        # Owner can still end their own session.
        response = client.post(
            f"/sessions/{session_id}/end", headers=_auth_headers(token2)
        )
        assert response.status_code == 200, response.text


def test_admin_can_manage_other_users_sessions():
    with TestClient(app) as client:
        _register(client, "sess_u4")
        admin_headers = _ensure_admin(client)
        token4 = _login(client, "sess_u4")
        ws_id = _seed_workstation("sess-ws-3")

        session_id = (
            client.post(
                "/sessions/start",
                json={"workstation_id": ws_id},
                headers=_auth_headers(token4),
            )
            .json()["id"]
        )

        response = client.get(f"/sessions/{session_id}", headers=admin_headers)
        assert response.status_code == 200, response.text

        response = client.get("/sessions", headers=admin_headers)
        assert response.status_code == 200
        assert session_id in {s["id"] for s in response.json()}

        response = client.post(f"/sessions/{session_id}/end", headers=admin_headers)
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "ended"


def test_double_start_conflicts_and_end_twice_conflicts():
    with TestClient(app) as client:
        _register(client, "sess_u5")
        headers = _auth_headers(_login(client, "sess_u5"))
        ws_id = _seed_workstation("sess-ws-4")
        ws_id2 = _seed_workstation("sess-ws-5")

        session_id = (
            client.post(
                "/sessions/start", json={"workstation_id": ws_id}, headers=headers
            )
            .json()["id"]
        )

        response = client.post(
            "/sessions/start", json={"workstation_id": ws_id2}, headers=headers
        )
        assert response.status_code == 409, response.text

        assert (
            client.post(f"/sessions/{session_id}/end", headers=headers).status_code
            == 200
        )
        response = client.post(f"/sessions/{session_id}/end", headers=headers)
        assert response.status_code == 409, response.text


def test_status_filter_validation():
    with TestClient(app) as client:
        _register(client, "sess_u6")
        headers = _auth_headers(_login(client, "sess_u6"))

        response = client.get("/sessions?status=bogus", headers=headers)
        assert response.status_code == 400, response.text

        response = client.get("/sessions?status=active", headers=headers)
        assert response.status_code == 200, response.text


def test_negative_duration_clamps_cost_to_zero(monkeypatch):
    """Clock skew (end before start) must not credit the customer."""

    class _PastDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return super().now(tz) - timedelta(hours=2)

    with TestClient(app) as client:
        _register(client, "sess_u7", balance=50.0)
        headers = _auth_headers(_login(client, "sess_u7"))
        ws_id = _seed_workstation("sess-ws-6")

        session_id = (
            client.post(
                "/sessions/start", json={"workstation_id": ws_id}, headers=headers
            )
            .json()["id"]
        )

        monkeypatch.setattr(
            "src.database.sessions.end.datetime", _PastDateTime
        )
        response = client.post(f"/sessions/{session_id}/end", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["cost"] == 0

        response = client.get("/auth/users/me", headers=headers)
        assert response.json()["balance"] == 50.0


def test_logout_requires_auth():
    with TestClient(app) as client:
        assert client.post("/auth/logout").status_code in (401, 403)
        assert client.post("/auth/logout", headers=_auth_headers("bad")).status_code in (
            401,
            403,
        )
