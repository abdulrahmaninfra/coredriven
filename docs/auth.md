# JWT Authentication Guide

Guide for using JWT-based authentication in this project.

## Overview

`src/core/security.py` provides the following helpers:

| Function | Description |
| --- | --- |
| `hash_password(plain_password)` | Hashes a plaintext password with argon2 |
| `verify_password(plain_password, hashed_password)` | Verifies a plaintext password against a stored hash |
| `create_access_token(data, expires_delta=None)` | Creates a signed JWT with an `exp` claim |
| `decode_token(token)` | Validates and decodes a JWT, returning `{}` on failure |

## Configuration

JWT settings are loaded from `.env` via `src/core/config.py`:

| Env var | Purpose |
| --- | --- |
| `PASSWORD_HASH_SECRET_KEY` | Signing secret for JWT encoding/decoding |
| `HASHING_ALGORITHM` | JWT signing algorithm (e.g. HS256) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime in minutes |

## Current implementation

Already in `src/core/security.py`:

```python
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return {}
```

## Integration steps (pending)

1. **Schemas** — add to `src/api/schema.py`:

   ```python
   class LoginRequest(BaseModel):
       username: str
       password: str

   class TokenResponse(BaseModel):
       access_token: str
       token_type: str = "bearer"
   ```

2. **Dependency** — add `get_current_user` to `src/core/security.py`:

   ```python
   def get_current_user(authorization: str = Header(...)) -> str:
       token = authorization.removeprefix("Bearer ")
       payload = decode_token(token)
       if not payload.get("sub"):
           raise HTTPException(status_code=401, detail="Invalid token")
       return payload["sub"]
   ```

3. **Endpoints** — in `src/api/auth.py`:
   - `POST /auth/login` — verify password against the DB, return `TokenResponse` with `sub=username`.
   - `POST /auth/register` — create the user (via `src/database/customers/create.py`), return a token.

4. **App** — build the FastAPI app in `src/main.py` and include the auth router. Serve with `uvicorn src.main:app`.

## Usage

Create a token on login:

```python
token = create_access_token({"sub": username})
```

Protect an endpoint:

```python
@app.get("/profile")
def profile(current_user: str = Depends(get_current_user)):
    return {"user": current_user}
```

## Client example

```http
POST /auth/login
Content-Type: application/json

{"username": "alice", "password": "secret"}
```

Response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Send the token on subsequent requests:

```http
GET /profile
Authorization: Bearer <jwt>
```

## Dependencies

`pyjwt` is required. It is declared in `pyproject.toml` but **not** in `requirement.txt`.
