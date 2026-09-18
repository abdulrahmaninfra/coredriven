FastAPI + SQLAlchemy 2 (ORM) POS / internet-cafe API. SQLite by default, Postgres-ready. Package manager is uv; Python 3.14 (requires-python >= 3.14, .python-version). All imports are absolute src.* — launch from repo root.

Last verified against main @ bace37e (2026-09-13). If this file and the code disagree, the code wins — then fix this file.

Commands
bash

uv sync --frozen                    # install exactly what uv.lock pins
uv run uvicorn main:app --port 9999 --reload   # dev server
uv run ruff check .                 # lint (CI runs this; currently 18 I001s, see Quirks)
uv run python -m pytest             # tests — zero env vars / .env needed (conftest.py pins everything)
uv run alembic upgrade head         # apply migrations
uv run alembic revision --autogenerate -m "..."   # new migration after model changes
uv run alembic check                # verify models match migrations (CI candidate)
uv add <pkg>                        # deps -> pyproject.toml + uv.lock
The FastAPI app instance in repo-root main.py is named app. Use main:app for uvicorn and from main import app for imports in tests.
pytest is configured with pythonpath = ["src"]; tests are plain modules in src/test/.
Environment / settings
src/core/config.py uses pydantic-settings + load_dotenv(). Copy .env.example to .env for local runs. Required (no defaults):

DATABASE_NAME, DATABASE_URL, HOST, PORT, JWT_ALGORITHM, PASSWORD_HASH_SECRET_KEY, JWT_ACCESS_TOKEN_EXPIRE_MINUTES, FIRST_SUPERADMIN_EMAIL, FIRST_SUPERADMIN_PASSWORD

Optional: LOGIN_MAX_FAILED_ATTEMPTS (default 5), LOGIN_WINDOW_SECONDS (default 900), ALLOWED_ORIGINS / ALLOWED_METHODS.

Gotchas:

get_settings() is lru_cached and read at module import time (security.py, database.py, rate_limit.py). Env changes need a fresh process.
PASSWORD_HASH_SECRET_KEY is misleadingly named: argon2 salts itself; this value is the JWT HMAC signing secret.
FIRST_SUPERADMIN_EMAIL is used as the superadmin username (there is no email column on Customer).
DATABASE_URL accepts a full SQLAlchemy URL; if it doesn't start with a known dialect it falls back to sqlite:///{DATABASE_NAME}.
Architecture
text

main.py                     app factory create_application(); lifespan: create_db() + seed first superadmin
src/api/routers/            auth, users, workstations, sessions, transactions (thin: validate + delegate)
src/api/schema.py           pydantic request/response models (money = Money/PositiveMoney = Decimal, 2dp)
src/api/errors.py           AppError -> HTTP status map + global handler
src/core/                   security (JWT + argon2), permissions (RBAC), rate_limit, config
src/database/<domain>/      one package per domain: models/read/create/update/delete
migrations/                 Alembic environment; initial revision d05a84907f4e
DB infrastructure (Base, engine, SessionLocal, create_db) lives in src/database/customers/database.py — historic; every domain imports from there.
Startup calls create_db() (create_all) and Alembic exists for real schema management — after changing a model, generate a migration; don't rely on create_all.
All timestamps are naive UTC (SQLite CURRENT_TIMESTAMP, 1-second resolution).
API surface (all JSON except login)
Router
Endpoints
auth	POST /auth/login (OAuth2 form: username+password) → {access_token}; GET /auth/me; PUT /auth/me (self-update: phone/password); POST /auth/logout
users	POST /users (admin: can_manage_users); GET /users (limit/offset); PUT /users/{id} (id or username); DELETE /users/{id}; GET /users/{id}/permissions (can_manage_admins); PUT /users/{id}/admin (role + permission flags)
workstations	GET /workstations; POST /workstations; PUT /workstations/{id}; DELETE /workstations/{id} (all write ops: can_manage_workstations)
sessions	POST /sessions (start; needs balance > 0); POST /sessions/{id}/end (charges cost); GET /sessions (filters: user_id, workstation_id, status=active|ended); GET /sessions/{id}
transactions	POST /transactions/recharge; POST /transactions/deduct (can_manage_billing; body: target_username, amount > 0, note?); GET /transactions (billing-read; username, limit)

Auth & permissions
JWT bearer tokens (Authorization: Bearer ...), OAuth2PasswordBearer on /auth/login.
Passwords: argon2 hashes.
RBAC: is_superadmin bypasses everything; sub-admins need is_admin plus a row in AdminPermission with granular flags: can_manage_admins, can_manage_users, can_manage_workstations, can_manage_billing (+ read_only_billing for read-only ledger access).
Login rate limiting: in-memory fixed window keyed by username — after LOGIN_MAX_FAILED_ATTEMPTS failures within LOGIN_WINDOW_SECONDS, all login attempts for that username (correct password included) get 429 until the window expires. Successful login clears the counter. Single-process only.
Money
All money is Decimal quantized to 2 dp (Money, PositiveMoney in schema.py); JSON still serializes as numbers.
Balance math: ROUND_HALF_EVEN; balances capped at 99999999.99 — exceeding it raises a domain error mapped to 400 (guards SQLite's silent column overflow).
Recharge/deduct are atomic (SAVEPOINT via begin_nested()); the transactions table is a signed-amount ledger with balance_after snapshots.
Errors
Domain errors (AppError subclasses in src/database/exceptions.py) are mapped to HTTP statuses in src/api/errors.py::ERROR_STATUS_MAP (404/400/403/409). Raise domain errors in new code; avoid raw HTTPException (a few legacy spots still use it — don't copy that). Unknown AppError types default to 400.

Testing
src/test/conftest.py pins all Settings env vars into a temp SQLite DB and resets the login limiter around every test — uv run python -m pytest works with zero configuration.
Conventions: per-module username prefixes (sess_*, adm_*, …) because all modules share one DB (settings are lru_cached); use with TestClient(app) as client so the lifespan runs; admins are created directly via CreateNewUser + flag flips, then logged in through POST /auth/login (form-encoded).
Current suite: 40 tests. New test modules set nothing themselves — conftest handles it.
Known quirks (verify before "fixing" — some are pending decisions)
note fields default to the literal string "null" in schema.py (not None) — stored that way in the ledger.
UserCreate.balance is accepted but ignored (new users always start at 0).
Balance top-ups via PUT /users/{id} do not create ledger rows — ledger and balance can diverge.
UserCharge in schema.py is dead code.
Model classes Sessions/Transactions are plural (rest are singular); UpdateUser is a PascalCase function.
transactions listing loads all rows then slices in Python (no SQL-level pagination yet).
Deleting a user does not guard against existing sessions/transactions (FK enforcement off in SQLite) — verify before assuming cascade behavior.