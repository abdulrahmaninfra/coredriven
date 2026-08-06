# AGENTS.md

FastAPI + SQLite (raw `sqlite3`) POS / internet-cafe API. Package manager is `uv`; Python 3.14 (`requires-python >= 3.14`, `.python-version`). All imports are absolute `src.*` — launch from repo root.

## Commands

```bash
uv run uvicorn src.api.main:auth --port 9999 --reload   # dev server
uv run ruff check .                                    # lint (CI runs this)
uv run python -m pytest                                # tests (CI runs this)
uv add <pkg>            # deps -> pyproject.toml + uv.lock
uv add --dev <pkg>      # dev group (pytest, ruff, httpx2)
uv sync --frozen        # CI install
```

- The FastAPI app instance in `src/api/main.py` is named **`auth`**, not `app` (renamed in commit 96dbbcb). Use `src.api.main:auth` for uvicorn.
- **Known broken state:** `src/test/test_auth.py:11` still does `from src.api.main import app`, so `pytest` currently fails at collection. Fix the import to `auth` when you touch tests. `docs/fixes-report.md` has the same stale `src.api.main:app` command.
- `pytest` is configured with `pythonpath = ["src"]`; there is no test runner in `src/test/__init__.py` conflict — tests are plain modules there.

## Environment / settings

- `src/core/config.py` calls `load_dotenv()` and requires a `.env` (`.env` is gitignored; copy `.env.example`). Fields like `DATABASE_NAME`, `HOST`, `PORT`, `JWT_*` have **no defaults** — the app won't import without them.
- `get_settings()` is `lru_cache`d, and `src/core/security.py` / `src/database/customers/connect.py` read settings at **module import time**. Env changes need a fresh process.
- Test pattern (follow it): set env vars at the top of the test module *before* importing `src.api.main`, e.g. `os.environ["DATABASE_NAME"] = tmp test db path`. Tests must never depend on the real `.env` DB.

## Architecture

- `src/api/` — FastAPI routers (`main.py` = app factory `create_auth_application()`, `auth.py` = auth router, `schema.py` = pydantic models).
- `src/core/` — `config.py` (settings), `security.py` (argon2 hashing via passlib, JWT via PyJWT, `get_current_user`).
- `src/database/customers/` — raw `sqlite3` data layer: classes `GetUser`, `CreateNewUser` take a connection injected via the `get_db_connection` dependency (yields `sqlite3.Row`).
- `create_db()` runs in the app lifespan: `CREATE TABLE IF NOT EXISTS customers`. New tables/schema changes go there.
- Auth: `POST /auth/register`, `POST /auth/login` (OAuth2 form-encoded, `OAuth2PasswordRequestForm`), `GET /auth/users/me` (Bearer token). Docs at `docs/auth.md`.

## Conventions / CI

- CI (`.github/workflows/gh.yml`) runs on `main`, `fit/**`, `fix/**`; commit messages use `type:` prefixes (`refactor:`, `fix:`, `test:`, `style:`, `chore:`).
- Ruff ignores `B008` (Depends in defaults — idiomatic FastAPI) and `BLE001` (broad except for error normalization); keep those patterns, don't "fix" them.
- The `customers.id` column has no type in the schema; `CreateNewUser` supplies `str(uuid.uuid4())`.
