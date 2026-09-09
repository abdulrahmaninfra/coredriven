# CoreDriven

POS and internet-cafe management API built with **FastAPI** + **SQLAlchemy**.
Customers register, log in, start timed sessions on workstations, and are
billed by the hour when the session ends (or when they log out).

## Stack

- Python ≥ 3.14, managed with [`uv`](https://docs.astral.sh/uv/)
- FastAPI + Uvicorn, Pydantic v2, SQLAlchemy 2.x (SQLite by default)
- Auth: OAuth2 password flow, argon2 password hashing, JWT (PyJWT)

## Quickstart

```bash
uv sync --frozen          # install dependencies
cp .env.example .env      # then fill in real values (see below)
uv run uvicorn main:app --port 9999 --reload
```

Interactive docs: `http://localhost:9999/docs`

### Environment

All variables in `.env.example` are required (the app won't import without
them). Key ones:

| Variable | Example | Notes |
|---|---|---|
| `HOST` / `PORT` | `0.0.0.0` / `9999` | Server bind |
| `DATABASE_NAME` | `coredriven.db` | SQLite fallback file |
| `DATABASE_URL` | `sqlite:///coredriven.db` | Used as-is if it starts with a known dialect (`sqlite`, `postgres`, …), otherwise falls back to `sqlite:///{DATABASE_NAME}` |
| `PASSWORD_HASH_SECRET_KEY` | `…min 32 chars…` | JWT signing secret (there is no separate `JWT_SECRET`) |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `60` | Token lifetime |

## How it works

```
admin creates + funds account → login (JWT) → POST /sessions/start {workstation_id}
    → … use the PC … → POST /auth/logout  (ends your session, bills you)
```

- Login is form-encoded (`username=` + `password=`), everything else is JSON.
- Accounts are created by admins (`POST /auth/admin/register`, new users
  start at balance 0) and funded via `PUT /auth/admin/update`.
  Users manage only their own phone/password via `PUT /auth/update`.
- Sessions are **self-scoped**: you can only start/end/read your own, unless
  your account has `is_admin`, in which case staff can manage anyone's.
- Billing: `cost = elapsed_hours × workstation.hourly_rate`, clamped at zero
  and capped at your remaining balance (balance never goes negative).
- Logout is idempotent; the JWT itself is not revoked, so clients must
  discard the token.
- Workstations are created by admins via `POST /workstations`.

### Endpoints

| Method & path | Auth | Description |
|---|---|---|
| `POST /auth/admin/register` | Admin | Create account (starts at balance 0) |
| `POST /auth/login` | – | OAuth2 form login → `{access_token}` |
| `POST /auth/logout` | Bearer | End your active session (idempotent) |
| `GET /auth/users/me` | Bearer | Your profile |
| `PUT /auth/update` | Bearer | Update your phone/password |
| `PUT /auth/admin/update` | Admin | Update any user (`target_username`, balance, `is_active`, rename) |
| `DELETE /auth/admin/delete` | Admin | Delete a user (`?username=` or `?phone_number=`) |
| `POST /sessions/start` | Bearer | Start a session on a workstation |
| `POST /sessions/{id}/end` | Bearer | End a session (owner or admin) |
| `GET /sessions` | Bearer | List sessions (self-only unless admin; `?status=active\|ended`) |
| `GET /sessions/{id}` | Bearer | One session (owner or admin) |
| `GET /workstations` | Bearer | List workstations |
| `POST /workstations` | Admin | Create a workstation |

## Development

```bash
uv run ruff check .        # lint (CI runs this)
uv run python -m pytest    # tests (CI runs this)
```

- The FastAPI app instance is named **`app`** (`main:app` in the repo-root
  `main.py`).
- Tests live in `src/test/` and set their own temp database via env vars
  before importing the app.
- Commit messages use `type:` prefixes (`feat:`, `fix:`, `test:`, `docs:`,
  `style:`, `chore:`, `refactor:`).

## Notes

- **No migrations**: tables are created via `Base.metadata.create_all()` at
  startup. If models change, delete the `.db` file and restart (dev only).
- Domain errors raised by the DB layer (`src/database/exceptions.py`) are
  translated to HTTP statuses by `src/api/errors.py`.
- More detail: `docs/sessions.md` (lifecycle, ownership, cost policy),
  `docs/auth.md`, `AGENTS.md` (repo conventions for AI agents).
