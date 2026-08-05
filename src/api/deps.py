import sqlite3

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from src.core.security import decode_token
from src.database.customers.connect import get_db_connection
from src.database.customers.read import GetUser

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    payload = decode_token(token)

    username = payload.get("sub")
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = GetUser(conn).get_user_by_username(username)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User no longer exists",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
