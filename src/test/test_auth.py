import os
import tempfile

os.environ["DATABASE_NAME"] = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["PASSWORD_HASH_SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"

from fastapi.testclient import TestClient

from src.api.main import auth


def test_register_login_and_current_user():
    with TestClient(auth) as client:
        response = client.post(
            "/auth/register",
            json={
                "username": "alice",
                "password": "secret123",
                "phone_number": "12345",
                "balance": 50.0,
            },
        )
        assert response.status_code == 201
        assert response.json()["username"] == "alice"

        response = client.post(
            "/auth/login", data={"username": "alice", "password": "secret123"}
        )
        assert response.status_code == 200
        token = response.json()["access_token"]

        response = client.get(
            "/auth/users/me", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        assert response.json()["username"] == "alice"
        assert response.json()["balance"] == 50.0


def test_register_duplicate_username():
    with TestClient(auth) as client:
        payload = {
            "username": "bob",
            "password": "secret123",
            "phone_number": "54321",
            "balance": 10.0,
        }
        assert client.post("/auth/register", json=payload).status_code == 201
        assert client.post("/auth/register", json=payload).status_code == 409


def test_login_wrong_password():
    with TestClient(auth) as client:
        client.post(
            "/auth/register",
            json={
                "username": "carol",
                "password": "secret123",
                "phone_number": "11111",
                "balance": 0.0,
            },
        )
        response = client.post(
            "/auth/login", data={"username": "carol", "password": "wrong"}
        )
        assert response.status_code == 401


def test_update_user_fields():
    with TestClient(auth) as client:
        payload = {
            "username": "dave",
            "password": "secret123",
            "phone_number": "22222",
            "balance": 10.0,
        }
        assert client.post("/auth/register", json=payload).status_code == 201

        token = client.post(
            "/auth/login", data={"username": "dave", "password": "secret123"}
        ).json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.put(
            "/auth/update",
            json={"phone_number": "99999", "balance": 42.5},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["phone_number"] == "99999"
        assert response.json()["balance"] == 42.5

        assert client.put("/auth/update", json={}, headers=headers).status_code == 400

        response = client.put(
            "/auth/update",
            json={"username": "dave2"},
            headers=headers,
        )
        assert response.status_code == 200
        assert response.json()["username"] == "dave2"

        assert (
            client.post(
                "/auth/login", data={"username": "dave2", "password": "secret123"}
            ).status_code
            == 200
        )
