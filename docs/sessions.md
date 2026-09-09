# Sessions: lifecycle, ownership, and logout

How internet-cafe sessions work in this API: a user logs in, explicitly starts
a session on a workstation, and logging out ends their active session.
Sessions are **self-scoped** — a user can only touch their own sessions —
unless `Customer.is_admin` is set, in which case staff can manage anyone's.

## Lifecycle

```
POST /auth/register            create account (balance funds the session)
POST /auth/login               get JWT (login itself creates NO session)
POST /sessions/start           {workstation_id} -> session (status "active")
... user occupies the workstation ...
POST /auth/logout              ends MY active session (idempotent)
  -- or --
POST /sessions/{id}/end        end one session by id (owner or admin only)
```

Login stays pure on purpose: picking a workstation can fail with
404/409, and authentication should never fail because a PC is occupied.
The kiosk/client chains `login` -> `start`.

## Ownership model

| Endpoint | Rule |
|---|---|
| `POST /sessions/start` | Self by construction: the session is created with `current_user.id`. |
| `POST /sessions/{id}/end` | Owner or admin, else **403**. |
| `GET /sessions/{id}` | Owner or admin, else **403**. |
| `GET /sessions` | Non-admins are forced to `user_id = me` (passing someone else's id is **403**). Admins keep the `user_id` / `workstation_id` / `status` filters. |
| `POST /auth/logout` | Owned by construction: the lookup is keyed on `current_user.id`, so no IDOR is possible. |
| `GET /workstations` | Shared resource, no per-user owner. Auth only. |

Enforcement is two layers: the router checks (`src/api/routers/sessions.py`)
and the service function takes `acted_by` (`end_session(db, session_id,
acted_by=...)` raises `NotYourSessionError` -> HTTP 403 via
`src/api/errors.py`). The second layer protects future callers that bypass
the router.

## Logout contract

`POST /auth/logout` (Bearer required):

- Active session found -> ends it, returns
  `{"detail": "Logged out.", "ended": true, "session": {SessionResponse}}`.
- None found -> `{"detail": "No active session.", "ended": false, "session": null}`
  with HTTP 200, so double-logout and retries are safe.
- The JWT itself is NOT revoked (stateless JWT, no blocklist): the client must
  discard the token. A replayed token can only `start` a new session, which is
  the accepted trade-off (see "Full token revocation" below if that changes).

## Cost policy

Computed in `end_session` (`src/database/sessions/end.py`):

- `cost = elapsed_hours * workstation.hourly_rate`, rounded to 2 decimals.
- **Clamped at zero**: clock skew can never produce a negative cost
  (which would credit the customer).
- **Capped at the remaining balance**: balance never goes negative; the cafe
  absorbs overruns.
- `Numeric` columns come back as `Decimal`, which cannot mix with `float`
  arithmetic, so values are coerced through `float()` before math.

## Workstations

- `GET /workstations` (Bearer) lists all workstations.
- `POST /workstations` (admin only, else **403**) creates one:
  `{"name": "pc-01", "hourly_rate": 10.0, "is_active": true}` -> **201**.
  Names must be unique (**409** if taken) and non-blank (**400**);
  `hourly_rate` must be > 0 (**400**). The id is a server-generated uuid and
  new workstations start `"status": "available"`, ready to host sessions.
  Logic lives in `CreateWorkstation` (`src/database/workstations/create.py`),
  mirroring `CreateNewUser`, with an `IntegrityError` catch so concurrent
  creates of the same name still resolve to **409**.

## Query validation

`GET /sessions?status=...` only accepts `active` / `ended`; anything else is
**400**. The router argument is named `status_filter` (query key stays
`status`) so it no longer shadows FastAPI's `status` import.

## What changed (files)

- `src/database/exceptions.py` — new `NotYourSessionError(AppError)`.
- `src/api/errors.py` — `NotYourSessionError` -> **403**.
- `src/database/sessions/end.py` — `end_session(..., acted_by=None)` ownership
  check; cost clamp/cap/round; float coercion.
- `src/database/sessions/start.py` — float coercion for `balance / hourly_rate`.
- `src/api/routers/sessions.py` — ownership on end/get/list; `status` validation.
- `src/api/routers/auth.py` — new `POST /auth/logout` (idempotent).
- `src/api/routers/workstations.py` — new admin-only `POST /workstations`.
- `src/api/schema.py` — new `WorkstationCreate`.
- `src/database/customers/models.py` — `Customer.is_admin` flag (drives the
  admin bypass).
- `src/test/test_sessions.py` — coverage: start->logout flow, cross-user 403s,
  admin bypass, double-start 409, end-twice 409, status validation,
  negative-duration clamp, logout-auth.
- `src/test/test_workstations.py` — coverage: admin create 201 + listed,
  non-admin 403, unauthenticated 401, duplicate 409, bad payload 400s,
  created workstation hosts a session.
- `AGENTS.md` — endpoint + router-path docs updated.

## Database note

There are no migrations (no Alembic): `create_db()` only creates missing
tables. **Fresh databases pick up `Customer.is_admin` automatically;
existing `.db` files must be recreated** (delete the file and restart) or the
column will be missing.

## Possible follow-ups (not implemented)

- **Full token revocation**: add `jti` to the JWT + a Redis blocklist
  (`redis` is already a dependency, currently unused) checked in
  `get_current_user`; logout revokes the token.
- **`expires_at` column**: `start` currently writes the balance-derived
  estimate into `end_time` and `end` overwrites it with the real end time.
  A separate column would stop active sessions from showing a future
  `end_time` with `cost: null`.
- Partial unique indexes in `src/database/sessions/models.py` use
  `sqlite_where` only; add `postgresql_where` (or handle `IntegrityError` ->
  409) before running on Postgres, and for the concurrent double-book race.

## Running the tests

```bash
uv run python -m pytest          # full suite (auth + sessions)
uv run python -m pytest src/test/test_sessions.py -v
uv run ruff check .              # lint
```
