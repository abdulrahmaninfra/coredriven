import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.schema import Token, UserCreate, UserResponse
from src.core.security import create_access_token, verify_password
from src.database.customers.connect import get_db_connection
from src.database.customers.create import CreateNewUser
from src.database.customers.read import GetUser

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, conn: sqlite3.Connection = Depends(get_db_connection)):
    """
    Register a new customer account.
    Returns the created customer's public profile (no password).
    """
    # Reject if username is already taken
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

        return dict(new_user)

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


@router.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """
    Login with username + password (standard OAuth2 form).
    Returns a Bearer JWT token on success.
    """
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
