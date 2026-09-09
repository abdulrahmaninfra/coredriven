import os
import tempfile

os.environ["DATABASE_NAME"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["PASSWORD_HASH_SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient

from main import app
from src.database.customers.create import CreateNewUser
from src.database.customers.database import SessionLocal
from src.database.customers.read import GetUser

# NOTE: "wsu_" prefix avoids rows colliding with the other test modules:
# get_settings() is lru_cached, so all modules share one database file.
# Users are created by an admin (public registration no longer exists).


def _login(client, username):
    response = client.post(
        "/auth/login", data={"username": username, "password": "secret123"}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


def _seed_admin(username):
    db = SessionLocal()
    try:
        if GetUser(db).get_user_by_username(username) is None:
            CreateNewUser(username, "secret123", f"555-{username}", 50.0).create_user(
                db
            )
        GetUser(db).get_user_by_username(username).is_admin = True
        db.commit()
    finally:
        db.close()


def _admin_headers(client, username):
    _seed_admin(username)
    return _headers(_login(client, username))


def _create_user(client, admin_headers, username, balance=50.0):
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


def test_admin_can_create_workstation():
    with TestClient(app) as client:
        headers = _admin_headers(client, "wsu_admin_1")

        response = client.post(
            "/workstations",
            json={"name": "wsu-ws-1", "hourly_rate": 10.0},
            headers=headers,
        )
        assert response.status_code == 201, response.text
        body = response.json()
        assert body["name"] == "wsu-ws-1"
        assert body["status"] == "available"
        assert body["hourly_rate"] == 10.0
        assert body["is_active"] is True
        assert body["id"]

        response = client.get("/workstations", headers=headers)
        assert response.status_code == 200
        assert "wsu-ws-1" in {ws["name"] for ws in response.json()}


def test_non_admin_cannot_create_workstation():
    with TestClient(app) as client:
        admin = _admin_headers(client, "wsu_admin_0")
        _create_user(client, admin, "wsu_user", balance=0.0)
        headers = _headers(_login(client, "wsu_user"))

        response = client.post(
            "/workstations",
            json={"name": "wsu-ws-2", "hourly_rate": 10.0},
            headers=headers,
        )
        assert response.status_code == 403, response.text

        assert client.post("/workstations", json={"name": "x"}).status_code == 401


def test_duplicate_name_conflicts():
    with TestClient(app) as client:
        headers = _admin_headers(client, "wsu_admin_2")
        payload = {"name": "wsu-ws-3", "hourly_rate": 10.0}

        assert client.post("/workstations", json=payload, headers=headers).status_code == 201
        response = client.post("/workstations", json=payload, headers=headers)
        assert response.status_code == 409, response.text


def test_invalid_payload_rejected():
    with TestClient(app) as client:
        headers = _admin_headers(client, "wsu_admin_3")

        for payload in (
            {"name": "wsu-ws-4", "hourly_rate": 0},
            {"name": "wsu-ws-5", "hourly_rate": -5},
            {"name": "   ", "hourly_rate": 10.0},
            {"name": "", "hourly_rate": 10.0},
        ):
            response = client.post("/workstations", json=payload, headers=headers)
            assert response.status_code == 400, (payload, response.text)


def test_created_workstation_can_host_session():
    with TestClient(app) as client:
        headers = _admin_headers(client, "wsu_admin_4")
        ws_id = (
            client.post(
                "/workstations",
                json={"name": "wsu-ws-6", "hourly_rate": 10.0},
                headers=headers,
            )
            .json()["id"]
        )

        response = client.post(
            "/sessions/start", json={"workstation_id": ws_id}, headers=headers
        )
        assert response.status_code == 201, response.text
        assert response.json()["workstation_id"] == ws_id
