# AGENTS.md

FastAPI + SQLAlchemy ORM POS / internet-cafe API (SQLite backend). Package manager is `uv`; Python 3.14 (`requires-python >= 3.14`, `.python-version`). All imports are absolute `src.*` — launch from repo root.

## Commands

```bash
uv run uvicorn src.api.main:auth --port 9999 --reload   # dev server
uv run ruff check .                                    # lint (CI runs this)
uv run python -m pytest                                # tests (CI runs this)
uv add <pkg>            # deps -> pyproject.toml + uv.lock
uv add --dev <pkg>      # dev group (pytest, ruff, httpx2)
uv sync --frozen        # CI install
```

- The FastAPI app instance in `src/api/main.py` is named **`auth`**, not `app`. Use `src.api.main:auth` for uvicorn and for imports in tests.
- `pytest` is configured with `pythonpath = ["src"]`; no runner conflicts — tests are plain modules in `src/test/`.
- (No longer relevant: the app was migrated from raw `sqlite3` to SQLAlchemy in commit `c34630a`.)

## Environment / settings

- `src/core/config.py` calls `load_dotenv()` and `Settings` has **no defaults** for `DATABASE_NAME`, `DATABASE_URL`, `HOST`, `PORT`, `JWT_ALGORITHM`, `PASSWORD_HASH_SECRET_KEY`, `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` — the app won't import without all of them. `.env.example` is missing `DATABASE_URL`, so a fresh `.env` must add it too.
- The JWT signing secret is `PASSWORD_HASH_SECRET_KEY` (there is no `JWT_SECRET` field).
- `get_settings()` is `lru_cache`d and `src/core/security.py` / `src/database/customers/database.py` read settings at **module import time**. Env changes need a fresh process.
- Test pattern (follow it): set env vars at the top of the test module *before* importing `src.api.main`, e.g. `os.environ["DATABASE_NAME"] = tmp test db path`. Tests set only `DATABASE_NAME`/JWT vars; remaining required fields still fall through to the real `.env` via `load_dotenv()`, so they are not fully isolated from it.

## Architecture

- `src/api/` — FastAPI routers (`main.py` = app factory `create_auth_application()` producing the `auth` instance + middleware, wires routers and the exception handler; `routers/auth.py`, `routers/sessions.py`, `routers/workstations.py` = routers; `errors.py` = `AppError` → HTTP status mapping + handler; `schema.py` = pydantic models). `main.py` has a `if __name__ == "__main__"` block that serves with uvicorn via `uv run python -m src.api.main`.
- `src/core/` — `config.py` (settings), `security.py` (argon2 via passlib, JWT via PyJWT, `get_current_user`, `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")`).
- `src/database/` — SQLAlchemy layer:
  - `customers/database.py` — `engine`, `SessionLocal`, `Base`, `create_db()`, and the `get_db` dependency yielding a `Session`. Engine URL resolved by `_resolve_database_url()`: if `DATABASE_URL` starts with a known dialect (`sqlite`, `postgres`, `mysql`, …) it is used as-is, otherwise it falls back to `sqlite:///{DATABASE_NAME}`. `connect_args["check_same_thread"] = False` only for SQLite.
  - `customers/models.py` — `Customer` ORM model (`customers` table, `id` = `String` PK supplied as `uuid4` by callers).
  - `customers/create.py` / `read.py` / `update.py` / `delete.py` — classes `CreateNewUser`, `GetUser`, `UpdateUser`, `DeleteUser`; take the `Session` and return ORM instances/booleans.
  - `sessions/` — `models.py` (`Sessions` ORM model), `start.py` / `end.py` (`start_session`, `end_session`), `read.py` (`GetSession` with filters + `get_session_by_id`).
  - `workstations/` — `models.py` (`Workstation` ORM model), `read.py` (`GetWorkstation`).
  - `exceptions.py` — domain error hierarchy rooted at `AppError` (`UserNotFoundError`, `WorkstationUnavailableError`, `SessionNotFoundError`, `CustomerNotFoundError`, etc.); raised by the DB layer and translated to HTTP by `src/api/errors.py`.
- `create_db()` runs in the app lifespan (`Base.metadata.create_all`). New tables go on `Base` in the relevant `models.py`; schema changes are not migrated (no Alembic).
- Endpoints: auth (`/auth`): `POST /register`, `POST /login` (OAuth2 form-encoded, `OAuth2PasswordRequestForm`), `POST /logout` (Bearer, ends caller's active session, idempotent), `PUT /update`, `DELETE /delete`, `GET /users/me` (Bearer). Sessions (`/sessions`, all Bearer, self-scoped unless `Customer.is_admin`): `POST /sessions/start`, `POST /sessions/{session_id}/end`, `GET /sessions`, `GET /sessions/{session_id}`. Workstations (`/workstations`): `GET /workstations` (Bearer), `POST /workstations` (admin-only). Docs at `docs/auth.md` and `docs/sqlalchemy-migration-plan.md`.

## Conventions / CI

- CI (`.github/workflows/gh.yml`) runs ruff + pytest on push/PR to `main`, `fit/**`, `fix/**`; commit messages use `type:` prefixes (`refactor:`, `fix:`, `test:`, `style:`, `chore:`).
- Ruff ignores `B008` (Depends in defaults — idiomatic FastAPI) and `BLE001` (broad except for error normalization); keep those patterns, don't "fix" them.