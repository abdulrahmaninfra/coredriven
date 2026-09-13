import os
import tempfile
import time
from collections import deque

_tmp_db = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["DATABASE_NAME"] = _tmp_db
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["PASSWORD_HASH_SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["HOST"] = "127.0.0.1"
os.environ["PORT"] = "8000"
os.environ["FIRST_SUPERADMIN_EMAIL"] = "seed-admin@test.local"
os.environ["FIRST_SUPERADMIN_PASSWORD"] = "test-superadmin-password-123"

import time as _time

import pytest
from fastapi.testclient import TestClient

from main import app
from src.core.rate_limit import login_limiter

ADMIN = "seed-admin@test.local"
ADMIN_PASSWORD = "test-superadmin-password-123"


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, username: str, password: str):
    return client.post("/auth/login", data={"username": username, "password": password})


def _admin_headers(client: TestClient) -> dict:
    response = _login(client, ADMIN, ADMIN_PASSWORD)
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _create_user(client: TestClient, headers: dict, username: str, password: str = "secret123"):
    response = client.post(
        "/users",
        headers=headers,
        json={"username": username, "password": password, "phone_number": "0100000000"},
    )
    assert response.status_code == 201, response.text


def test_repeated_failures_lock_username(client):
    """5 wrong passwords trigger the lockout, even for the correct password."""
    headers = _admin_headers(client)
    _create_user(client, headers, "rl_lock")

    for _ in range(5):
        response = _login(client, "rl_lock", "wrong-password")
        assert response.status_code == 401, response.text

    # correct password is also rejected while locked out
    response = _login(client, "rl_lock", "secret123")
    assert response.status_code == 429, response.text
    assert "Too many failed login attempts" in response.json()["detail"]

    # a different username is unaffected
    _create_user(client, headers, "rl_other")
    assert _login(client, "rl_other", "secret123").status_code == 200


def test_successful_login_resets_counter(client):
    """Failures before a successful login do not carry over."""
    headers = _admin_headers(client)
    _create_user(client, headers, "rl_reset")

    for _ in range(4):
        assert _login(client, "rl_reset", "wrong-password").status_code == 401

    # a success clears the history
    assert _login(client, "rl_reset", "secret123").status_code == 200

    # 4 more failures stay below the threshold: 401, not 429
    for _ in range(4):
        response = _login(client, "rl_reset", "wrong-password")
        assert response.status_code == 401, response.text


def test_unknown_username_is_also_limited(client):
    """Guessing non-existent usernames hits the same window."""
    for _ in range(5):
        assert _login(client, "rl_ghost", "whatever").status_code == 401

    assert _login(client, "rl_ghost", "whatever").status_code == 429


def test_lockout_expires_after_window(client):
    """Once the window's oldest failure ages out, login works again."""
    headers = _admin_headers(client)
    _create_user(client, headers, "rl_expiry")

    for _ in range(5):
        assert _login(client, "rl_expiry", "wrong-password").status_code == 401
    assert _login(client, "rl_expiry", "secret123").status_code == 429

    # simulate the window passing: backdate every recorded failure
    window = login_limiter.window_seconds
    backdated = deque([_time.monotonic() - (window + 1)])
    login_limiter._attempts["rl_expiry"] = backdated

    assert _login(client, "rl_expiry", "secret123").status_code == 200