import os
import tempfile


# NEW — paste this instead:
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

# NOTE: "adm_" prefix avoids rows colliding with the other test modules:
# get_settings() is lru_cached, so all modules share one database file.
# Users are created by admins (public registration no longer exists) and
# start at balance 0 until an admin tops them up.


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


def _login(client, username, password="secret123"):
    response = client.post(
        "/auth/login", data={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token):
    return {"Authorization": f"Bearer {token}"}


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
    assert response.json()["balance"] == 0.0
    if balance:
        response = client.put(
            "/auth/admin/update",
            json={"target_username": username, "balance": balance},
            headers=admin_headers,
        )
        assert response.status_code == 200, response.text
    return response.json()


def test_admin_can_register_user_and_login():
    with TestClient(app) as client:
        admin = _admin_headers(client, "adm_admin_1")

        response = client.post(
            "/auth/admin/register",
            json={
                "username": "adm_alice",
                "password": "secret123",
                "phone_number": "12345",
                "balance": 50.0,
            },
            headers=admin,
        )
        assert response.status_code == 201, response.text
        assert response.json()["username"] == "adm_alice"

        # Duplicate username conflicts.
        assert (
            client.post(
                "/auth/admin/register",
                json={
                    "username": "adm_alice",
                    "password": "secret123",
                    "phone_number": "12345",
                    "balance": 0.0,
                },
                headers=admin,
            ).status_code
            == 409
        )

        # Funded by admin, the user can log in and read their profile.
        client.put(
            "/auth/admin/update",
            json={"target_username": "adm_alice", "balance": 50.0},
            headers=admin,
        )
        token = _login(client, "adm_alice")
        response = client.get("/auth/users/me", headers=_headers(token))
        assert response.status_code == 200
        assert response.json()["username"] == "adm_alice"
        assert response.json()["balance"] == 50.0


def test_register_requires_admin():
    with TestClient(app) as client:
        admin = _admin_headers(client, "adm_admin_2")
        _create_user(client, admin, "adm_bob", balance=0.0)
        user_headers = _headers(_login(client, "adm_bob"))

        payload = {
            "username": "adm_eve",
            "password": "secret123",
            "phone_number": "99999",
            "balance": 0.0,
        }
        response = client.post(
            "/auth/admin/register", json=payload, headers=user_headers
        )
        assert response.status_code == 403, response.text

        assert client.post("/auth/admin/register", json=payload).status_code == 401


def test_login_wrong_password():
    with TestClient(app) as client:
        admin = _admin_headers(client, "adm_admin_3")
        _create_user(client, admin, "adm_carol", balance=0.0)
        response = client.post(
            "/auth/login", data={"username": "adm_carol", "password": "wrong"}
        )
        assert response.status_code == 401


def test_update_self():
    with TestClient(app) as client:
        admin = _admin_headers(client, "adm_admin_4")
        _create_user(client, admin, "adm_dave", balance=10.0)
        headers = _headers(_login(client, "adm_dave"))

        response = client.put(
            "/auth/update", json={"phone_number": "99999"}, headers=headers
        )
        assert response.status_code == 200, response.text
        assert response.json()["phone_number"] == "99999"

        # No valid fields -> 400.
        assert client.put("/auth/update", json={}, headers=headers).status_code == 400

        # Privileged fields are not self-service: ignored, so still 400 and
        # the balance is unchanged.
        response = client.put(
            "/auth/update", json={"balance": 9999.0}, headers=headers
        )
        assert response.status_code == 400, response.text
        assert (
            client.get("/auth/users/me", headers=headers).json()["balance"] == 10.0
        )

        # Password change works and the new password logs in.
        assert (
            client.put(
                "/auth/update", json={"password": "newsecret123"}, headers=headers
            ).status_code
            == 200
        )
        _login(client, "adm_dave", password="newsecret123")


def test_admin_update_targets_users():
    with TestClient(app) as client:
        admin = _admin_headers(client, "adm_admin_5")
        _create_user(client, admin, "adm_erin", balance=0.0)
        _create_user(client, admin, "adm_fred", balance=0.0)
        user_headers = _headers(_login(client, "adm_erin"))

        # Non-admins are rejected from the admin endpoint.
        response = client.put(
            "/auth/admin/update",
            json={"target_username": "adm_erin", "balance": 42.5},
            headers=user_headers,
        )
        assert response.status_code == 403, response.text

        # Admin funds another user by target.
        response = client.put(
            "/auth/admin/update",
            json={"target_username": "adm_erin", "balance": 42.5},
            headers=admin,
        )
        assert response.status_code == 200, response.text
        assert response.json()["balance"] == 42.5

        # Unknown target -> 404.
        response = client.put(
            "/auth/admin/update",
            json={"target_username": "adm_nobody", "balance": 1.0},
            headers=admin,
        )
        assert response.status_code == 404, response.text

        # Rename collision -> 409.
        response = client.put(
            "/auth/admin/update",
            json={"target_username": "adm_erin", "username": "adm_fred"},
            headers=admin,
        )
        assert response.status_code == 409, response.text


def test_admin_can_delete_user():
    with TestClient(app) as client:
        admin = _admin_headers(client, "adm_admin_6")
        _create_user(client, admin, "adm_gail", balance=0.0)
        user_headers = _headers(_login(client, "adm_gail"))

        # Non-admins cannot delete.
        response = client.delete(
            "/auth/admin/delete?username=adm_gail", headers=user_headers
        )
        assert response.status_code == 403, response.text

        # Missing identifier -> 400.
        response = client.delete("/auth/admin/delete", headers=admin)
        assert response.status_code == 400, response.text

        # Unknown user -> 404.
        response = client.delete(
            "/auth/admin/delete?username=adm_nobody", headers=admin
        )
        assert response.status_code == 404, response.text

        # Delete works and the user can no longer log in.
        response = client.delete("/auth/admin/delete?username=adm_gail", headers=admin)
        assert response.status_code == 200, response.text
        assert (
            client.post(
                "/auth/login", data={"username": "adm_gail", "password": "secret123"}
            ).status_code
            == 401
        )
