from datetime import datetime, timedelta, timezone

import jwt
from passlib.hash import argon2
from src.core.config import Settings

settings = Settings()


SECRET_KEY = settings.PASSWORD_HASH_SECRET_KEY
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES



def hash_password(plain_password: str) -> str:
    return argon2.hash(plain_password)
       


def verify_password(plain_password: str, hashed_password: str) -> bool:  
    try:
        return argon2.verify(plain_password, hashed_password)
    except Exception:
        return False


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
    except jwt.PyJWTError as e:
        print(f"Error decoding token: {e}")
        return {}
    


