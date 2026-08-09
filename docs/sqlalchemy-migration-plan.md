# SQLite3 → SQLAlchemy Migration Plan

**Status:** Proposed · **Target:** Sync SQLAlchemy 2.0 (Session) · **Date:** 2026-08-06

## 1. Why migrate

| Current (raw `sqlite3`) | With SQLAlchemy |
| --- | --- |
| Hand-written SQL strings in 5 files; typo-prone | Typed ORM models with validated column types |
| `sqlite3.Row` dict-style access (`user["x"]`) | Attribute access (`user.x`) + type safety |
| Manual `conn.commit()` / `conn.rollback()` everywhere | Session handles lifecycle via a FastAPI dependency |
| Dynamic `SET`/`WHERE` built by string concat | Expressive query API with parameterized expressions |
| Tied to SQLite only | Swap one URL to support Postgres/MySQL later |
| No schema introspection / migration story | `Base.metadata.create_all()` now; Alembic later |

## 2. Current architecture (before)

| File | Role |
| --- | --- |
| `src/database/customers/connect.py` | `create_db()` (raw `CREATE TABLE`), `get_db_connection()` (yields `sqlite3.Row` conn) |
| `src/database/customers/create.py` | `CreateNewUser` — `INSERT` |
| `src/database/customers/read.py` | `GetUser` — `SELECT` (all / by username / by phone / fuzzy) |
| `src/database/customers/update.py` | `UpdateUser` — dynamic `UPDATE` |
| `src/database/customers/delete.py` | `DeleteUser` — `DELETE` by username / phone |
| `src/api/auth.py` | Depends `get_db_connection`; `dict(new_user)`; `user["password_hash"]`, `user["is_active"]` |
| `src/core/security.py` | `get_current_user` Depends `get_db_connection`; `user["is_active"]` |
| `src/api/main.py` | lifespan calls `create_db()` |

## 3. Target architecture (after)

```
src/database/customers/
├── database.py     # NEW: engine, SessionLocal, Base, get_db, create_db()
├── models.py       # NEW: Customer ORM model (Mapped / mapped_column)
├── create.py       # SWAP: ORM insert, same CreateNewUser API
├── read.py         # SWAP: ORM select, same GetUser API
├── update.py       # SWAP: ORM update, same UpdateUser API
├── delete.py       # SWAP: ORM delete, same DeleteUser API
└── connect.py      # DELETE (superseded by database.py)
```

- **Sync** `sqlite:///{DATABASE_NAME}` URL built from existing `DATABASE_NAME` setting (engine created once at import, same "fresh process for env changes" caveat as today).
- **Session per request** via a `get_db()` generator dependency (commit/rollback/close handled centrally).
- Existing class/function names and signatures preserved → `auth.py`/`security.py` only change data access (`user["x"]` → `user.x`) and error types.

## 4. Dependencies

```bash
uv add sqlalchemy
```

## 5. Migration steps

1. **Add dependency** — `uv add sqlalchemy`.
2. **`src/database/customers/database.py`** — engine, `SessionLocal = sessionmaker(...)`, `class Base(DeclarativeBase)`, `create_db()` → `Base.metadata.create_all(engine)`, `get_db()` dependency yielding `SessionLocal`.
3. **`src/database/customers/models.py`** — `Customer` model mirroring the current table (see §6 column mapping).
4. **`create.py`** — keep `CreateNewUser`; take a `Session`, `db.add()/commit()/refresh()`, return the model.
5. **`read.py`** — keep `GetUser`; use `db.query(Customer).filter(...)`, `.first()` / `.all()`.
6. **`update.py`** — keep `UpdateUser`; dynamic values dict + `db.query(...).update(values)`.
7. **`delete.py`** — keep `DeleteUser`; `db.query(...).delete()` + commit.
8. **`connect.py`** — delete; update imports in `main.py` (lifespan `create_db`), `auth.py`, `security.py`.
9. **`auth.py` / `security.py`** — `conn: sqlite3.Connection = Depends(...)` → `db: Session = Depends(get_db)`; attribute access; catch `SQLAlchemyError` instead of `sqlite3.Error`; drop `dict(new_user)` → return model.
10. **`src/api/schema.py`** — `ConfigDict(from_attributes=True)` on `UserResponse` so ORM models serialize directly.
11. **Tests** — `src/test/test_auth.py:11` fix stale `from src.api.main import app` → `auth`; keep env-set-before-import pattern with temp `DATABASE_NAME`.
12. **Verify** — `uv run ruff check .` + `uv run python -m pytest` + smoke test on :9999.

## 6. Column mapping

| Table `customers` | ORM `Customer` |
| --- | --- |
| `id` (no type, PK, UUID string) | `id: Mapped[str] = mapped_column(String, primary_key=True)` |
| `username VARCHAR(50) UNIQUE NOT NULL` | `username: Mapped[str] = mapped_column(String(50), unique=True)` |
| `phone_number VARCHAR(20) NOT NULL` | `phone_number: Mapped[str] = mapped_column(String(20))` |
| `password_hash VARCHAR(255) NOT NULL` | `password_hash: Mapped[str] = mapped_column(String(255))` |
| `balance DECIMAL(10,2) DEFAULT 0` | `balance: Mapped[float] = mapped_column(Numeric(10,2), default=0)` |
| `created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP` | `created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())` |
| `is_active BOOLEAN DEFAULT TRUE` | `is_active: Mapped[bool] = mapped_column(Boolean, default=True)` |

## 7. CRUD comparison — SQL vs ORM

### Create

```python
# SQL (today: src/database/customers/create.py)
cursor = conn.cursor()
cursor.execute(
    "INSERT INTO customers (id, username, password_hash, balance, phone_number)"
    " VALUES (?, ?, ?, ?, ?)",
    (self.id, self.username, self.password, self.balance, self.phone_number),
)
conn.commit()
cursor.execute("SELECT * FROM customers WHERE id = ?", (self.id,))
return cursor.fetchone()

# ORM (target)
customer = Customer(
    id=str(uuid.uuid4()),
    username=self.username,
    password_hash=self.password,
    balance=self.balance,
    phone_number=self.phone_number,
)
db.add(customer)
db.commit()
db.refresh(customer)
return customer
```

### Read — all users

```python
# SQL
cursor = conn.cursor()
cursor.execute("SELECT * FROM customers;")
return cursor.fetchall()

# ORM
return db.query(Customer).all()
```

### Read — by username

```python
# SQL
cursor.execute("SELECT * FROM customers WHERE username = ?", (username,))
return cursor.fetchone()

# ORM
return db.query(Customer).filter(Customer.username == username).first()
```

### Read — fuzzy search (`get_user`)

```python
# SQL
conditions, params = [], []
if username is not None:
    conditions.append("username LIKE ?")
    params.append(f"%{username}%")
if phone_number is not None:
    conditions.append("phone_number LIKE ?")
    params.append(f"%{phone_number}%")
query = "SELECT * FROM customers"
if conditions:
    query += " WHERE " + " AND ".join(conditions)
cursor.execute(query, params)
return cursor.fetchall()

# ORM
query = db.query(Customer)
if username is not None:
    query = query.filter(Customer.username.like(f"%{username}%"))
if phone_number is not None:
    query = query.filter(Customer.phone_number.like(f"%{phone_number}%"))
return query.all()
```

### Update

```python
# SQL
set_clause = ", ".join(conditions)   # built from string literals
query = f"UPDATE customers SET {set_clause} WHERE username = ?"
cursor.execute(query, params)
conn.commit()
return True

# ORM
values = {}
if username is not None:      values["username"] = username
if phone_number is not None:  values["phone_number"] = phone_number
if password is not None:      values["password_hash"] = _hash_password(password)
if balance is not None:       values["balance"] = balance
if is_active is not None:     values["is_active"] = is_active
if not values:
    return False
result = db.query(Customer).filter(Customer.username == current_username).update(values)
db.commit()
return result > 0
```

### Delete

```python
# SQL
cursor = conn.cursor()
cursor.execute("DELETE FROM customers WHERE phone_number = ?", (self.phone_number,))
conn.commit()
return True

# ORM
deleted = db.query(Customer).filter(Customer.phone_number == self.phone_number).delete()
db.commit()
return deleted > 0
```

## 8. Risks & gotchas

- **Import-time engine/session** — settings read at module import (`get_settings()` is `lru_cache`d); env changes need a fresh process. Tests must keep setting env before importing `src.api.main`.
- **Row access** — `user["password_hash"]`, `user["is_active"]`, `dict(user)` all change to attribute access. `security.py` and `auth.py` must be updated together or auth breaks at runtime.
- **Exceptions** — `except sqlite3.Error` → `except SQLAlchemyError` (`from sqlalchemy.exc`). Duplicate username raises `IntegrityError` if the pre-check is ever removed.
- **Session lifecycle** — `get_db()` must commit/rollback/close; never return unbound `DetachedInstance` to the response model without `from_attributes=True`.
- **Bulk update/delete** — `Query.update()`/`delete()` need explicit `db.commit()`; they bypass session identity-map sync (acceptable here).
- **Schema drift** — `create_all()` won't alter existing tables; the `customers.id` column gains an explicit type. Alembic is recommended as a follow-up.

## 9. Verification

```bash
uv run ruff check .           # lint clean
uv run python -m pytest       # tests pass (3, incl. fixed `auth` import)
uv run uvicorn src.api.main:auth --port 9999 --reload   # smoke: register → login → /users/me
```

## 10. Rollback

Revert the migration commit; `connect.py` + raw-sqlite modules are git-tracked and restored as-is. No data migration is required (same table name/columns via `create_all`).
