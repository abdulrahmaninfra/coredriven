"""Shared pytest fixtures.

The login rate limiter (src/core/rate_limit.py) is a process-wide
singleton; without a reset, failed logins from one test would leak into
the next (429s in unrelated tests). Clear its state around every test.

conftest.py is imported before test modules, so the Settings env pins
must live here too: importing rate_limit calls get_settings() eagerly.
"""

import os
import tempfile

_tmp_db = os.path.join(tempfile.mkdtemp(), "conftest.db")
os.environ["DATABASE_NAME"] = _tmp_db
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp_db}"
os.environ["PASSWORD_HASH_SECRET_KEY"] = "test-secret-key-that-is-longer-than-32-bytes"
os.environ["JWT_ALGORITHM"] = "HS256"
os.environ["JWT_ACCESS_TOKEN_EXPIRE_MINUTES"] = "30"
os.environ["HOST"] = "127.0.0.1"
os.environ["PORT"] = "8000"
os.environ["FIRST_SUPERADMIN_EMAIL"] = "seed-admin@test.local"
os.environ["FIRST_SUPERADMIN_PASSWORD"] = "test-superadmin-password-123"

import pytest

from src.core.rate_limit import login_limiter


@pytest.fixture(autouse=True)
def _reset_login_limiter():
    login_limiter._attempts.clear()
    yield
    login_limiter._attempts.clear()