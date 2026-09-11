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
        admin = GetUser(db).get_user_by_username(username)
        admin.is_admin = True
        admin.is_superadmin = True
        db.commit()
    finally:
        db.close()


def _admin_headers(client, username):
    _seed_admin(username)
    return _headers(_login(client, username))


def _create_user(client, admin_headers, username, balance=50.0):
    response = client.post(
        "/users",
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
            f"/users/{username}",
            json={"balance": balance},
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
            "/sessions", json={"workstation_id": ws_id}, headers=headers
        )
        assert response.status_code == 201, response.text
        assert response.json()["workstation_id"] == ws_id


def test_admin_can_update_workstation():
    with TestClient(app) as client:
        headers = _admin_headers(client, "wsu_admin_5")
        ws_id = (
            client.post(
                "/workstations",
                json={"name": "wsu-ws-7", "hourly_rate": 10.0},
                headers=headers,
            )
            .json()["id"]
        )

        response = client.put(
            f"/workstations/{ws_id}",
            json={"name": "wsu-ws-7b", "hourly_rate": 15.5, "is_active": False},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["name"] == "wsu-ws-7b"
        assert body["hourly_rate"] == 15.5
        assert body["is_active"] is False
        assert body["status"] == "available"

        names = {
            ws["name"]
            for ws in client.get("/workstations", headers=headers).json()
        }
        assert "wsu-ws-7b" in names
        assert "wsu-ws-7" not in names


def test_update_validation():
    with TestClient(app) as client:
        headers = _admin_headers(client, "wsu_admin_6")
        user_headers = _headers(
            _login(
                client,
                _create_user(client, headers, "wsu_user_2", balance=0.0)["username"],
            )
        )
        ws8_id = (
            client.post(
                "/workstations",
                json={"name": "wsu-ws-8", "hourly_rate": 10.0},
                headers=headers,
            )
            .json()["id"]
        )
        client.post(
            "/workstations",
            json={"name": "wsu-ws-9", "hourly_rate": 10.0},
            headers=headers,
        )

        # Unknown workstation -> 404.
        assert (
            client.put(
                "/workstations/wsu-nope",
                json={"hourly_rate": 20.0},
                headers=headers,
            ).status_code
            == 404
        )

        # Rename collision -> 409.
        response = client.put(
            f"/workstations/{ws8_id}",
            json={"name": "wsu-ws-9"},
            headers=headers,
        )
        assert response.status_code == 409, response.text

        # Bad rate / empty body -> 400; missing id -> 405.
        for path, payload, expected in (
            (f"/workstations/{ws8_id}", {"hourly_rate": 0}, 400),
            (f"/workstations/{ws8_id}", {"hourly_rate": -3}, 400),
            (f"/workstations/{ws8_id}", {"name": "   "}, 400),
            (f"/workstations/{ws8_id}", {}, 400),
            ("/workstations", {"hourly_rate": 20.0}, 405),
        ):
            response = client.put(path, json=payload, headers=headers)
            assert response.status_code == expected, (path, payload, response.text)

        # status is not user-editable: ignored, other fields still apply.
        response = client.put(
            f"/workstations/{ws8_id}",
            json={"status": "occupied", "hourly_rate": 20.0},
            headers=headers,
        )
        assert response.status_code == 200, response.text
        assert response.json()["status"] == "available"
        assert response.json()["hourly_rate"] == 20.0

        # Non-admin -> 403, anonymous -> 401.
        response = client.put(
            f"/workstations/{ws8_id}",
            json={"hourly_rate": 30.0},
            headers=user_headers,
        )
        assert response.status_code == 403, response.text
        assert (
            client.put(f"/workstations/{ws8_id}", json={"hourly_rate": 30.0})
        ).status_code == 401


def test_admin_can_delete_idle_workstation():
    with TestClient(app) as client:
        headers = _admin_headers(client, "wsu_admin_7")
        ws_id = (
            client.post(
                "/workstations",
                json={"name": "wsu-ws-10", "hourly_rate": 10.0},
                headers=headers,
            )
            .json()["id"]
        )

        response = client.delete(f"/workstations/{ws_id}", headers=headers)
        assert response.status_code == 200, response.text
        assert response.json()["ended_session_id"] is None

        names = {
            ws["name"]
            for ws in client.get("/workstations", headers=headers).json()
        }
        assert "wsu-ws-10" not in names

        # Second delete -> 404; missing id -> 405.
        assert (
            client.delete(f"/workstations/{ws_id}", headers=headers).status_code
            == 404
        )
        assert client.delete("/workstations", headers=headers).status_code == 405


def test_delete_occupied_workstation_ends_session():
    with TestClient(app) as client:
        admin = _admin_headers(client, "wsu_admin_8")
        _create_user(client, admin, "wsu_user_3", balance=50.0)
        user_headers = _headers(_login(client, "wsu_user_3"))
        ws_id = (
            client.post(
                "/workstations",
                json={"name": "wsu-ws-11", "hourly_rate": 10.0},
                headers=admin,
            )
            .json()["id"]
        )
        session_id = (
            client.post(
                "/sessions",
                json={"workstation_id": ws_id},
                headers=user_headers,
            )
            .json()["id"]
        )

        response = client.delete(f"/workstations/{ws_id}", headers=admin)
        assert response.status_code == 200, response.text
        assert response.json()["ended_session_id"] == session_id

        # Session was billed and closed; workstation is gone.
        assert (
            client.get(f"/sessions/{session_id}", headers=admin).json()["status"]
            == "ended"
        )
        assert client.get("/auth/me", headers=user_headers).json()["balance"] <= 50.0
        names = {
            ws["name"] for ws in client.get("/workstations", headers=admin).json()
        }
        assert "wsu-ws-11" not in names


def test_delete_requires_admin():
    with TestClient(app) as client:
        admin = _admin_headers(client, "wsu_admin_9")
        _create_user(client, admin, "wsu_user_4", balance=0.0)
        user_headers = _headers(_login(client, "wsu_user_4"))

        response = client.delete("/workstations/wsu-ws-1", headers=user_headers)
        assert response.status_code == 403, response.text
        assert client.delete("/workstations/wsu-ws-1").status_code == 401
