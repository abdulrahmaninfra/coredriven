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

- `src/api/` — FastAPI routers (`main.py` = app factory `create_auth_application()` producing the `auth` instance + middleware; `auth.py` = router; `schema.py` = pydantic models).
- `src/core/` — `config.py` (settings), `security.py` (argon2 via passlib, JWT via PyJWT, `get_current_user`, `oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")`).
- `src/database/customers/` — SQLAlchemy layer:
  - `database.py` — `engine` (hardcoded `sqlite:///{DATABASE_NAME}`, ignores the `DATABASE_URL` setting), `SessionLocal`, `Base`, `create_db()`, and the `get_db` dependency yielding a `Session`.
  - `models.py` — `Customer` ORM model (`customers` table, `id` = `String` PK supplied as `uuid4` by callers).
  - `create.py` / `read.py` / `update.py` / `delete.py` — classes `CreateNewUser`, `GetUser`, `UpdateUser`, `DeleteUser`; take the `Session` and return ORM instances/booleans.
- `create_db()` runs in the app lifespan (`Base.metadata.create_all`). New tables go on `Base` in `models.py`; schema changes are not migrated (no Alembic).
- Auth endpoints (prefix `/auth`): `POST /register`, `POST /login` (OAuth2 form-encoded, `OAuth2PasswordRequestForm`), `PUT /update`, `DELETE /delete`, `GET /users/me` (Bearer). Docs at `docs/auth.md` and `docs/sqlalchemy-migration-plan.md`.

## Conventions / CI

- CI (`.github/workflows/gh.yml`) runs ruff + pytest on push/PR to `main`, `fit/**`, `fix/**`; commit messages use `type:` prefixes (`refactor:`, `fix:`, `test:`, `style:`, `chore:`).
- Ruff ignores `B008` (Depends in defaults — idiomatic FastAPI) and `BLE001` (broad except for error normalization); keep those patterns, don't "fix" them.