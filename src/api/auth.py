import logging
import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.schema import Token, UserCreate, UserResponse
from src.core.security import create_access_token, get_current_user, verify_password
from src.database.customers.connect import get_db_connection
from src.database.customers.create import CreateNewUser
from src.database.customers.read import GetUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, conn: sqlite3.Connection = Depends(get_db_connection)):
    existing = GetUser(conn).get_user_by_username(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user_data.username}' is already taken.",
        )

    try:
        new_user = CreateNewUser(
            username=user_data.username,
            password=user_data.password,
            phone_number=user_data.phone_number,
            balance=user_data.balance,
        ).create_user(conn)

        if new_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create the user.",
            )

        return dict(new_user)

    except sqlite3.Error:
        logger.exception("Failed to register user '%s'", user_data.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create the user.",
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    user = GetUser(conn).get_user_by_username(form_data.username)

    if user is None or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user["is_active"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    access_token = create_access_token(data={"sub": user["username"]})
    return Token(access_token=access_token)


@router.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: dict = Depends(get_current_user)):
    return dict(current_user)
