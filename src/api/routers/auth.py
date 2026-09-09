import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.schema import (
    SessionResponse,
    Token,
    UserCreate,
    UserResponse,
    UserSelfUpdate,
    UserUpdate,
)
from src.core.security import create_access_token, get_current_user, verify_password
from src.database.customers.create import CreateNewUser
from src.database.customers.database import get_db
from src.database.customers.delete import DeleteUser
from src.database.customers.models import Customer
from src.database.customers.read import GetUser
from src.database.customers.update import UpdateUser
from src.database.exceptions import NotAdminError, UserNotFoundError
from src.database.sessions.end import end_session
from src.database.sessions.read import GetSession

logger = logging.getLogger(__name__)

auth = APIRouter(prefix="/auth", tags=["Authentication"])
admin = APIRouter(prefix="/auth/admin", tags=["Authentication"])


@admin.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register(
    user_data: UserCreate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):

    if not current_user.is_admin:
        raise NotAdminError("Only admins can register new users.")

    existing = GetUser(db).get_user_by_username(user_data.username)
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
            balance=0.0,
        ).create_user(db)

        if new_user is None:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create the user.",
            )

        return new_user

    except SQLAlchemyError:
        logger.exception("Failed to register user '%s'", user_data.username)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create the user.",
        )


@auth.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = GetUser(db).get_user_by_username(form_data.username)

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


@auth.put("/update", response_model=UserResponse)
def update_self(
    user_data: UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    updated = UpdateUser(
        db,
        current_username=current_user.username,
        phone_number=user_data.phone_number,
        password=user_data.password,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided to update.",
        )

    return GetUser(db).get_user_by_username(current_user.username)


@admin.put("/update", response_model=UserResponse)
def update_user(
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise NotAdminError("Only admins can update user information.")

    target = user_data.target_username or current_user.username
    if GetUser(db).get_user_by_username(target) is None:
        raise UserNotFoundError(f"User '{target}' not found.")

    if user_data.username is not None and user_data.username != target:
        existing = GetUser(db).get_user_by_username(user_data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{user_data.username}' is already taken.",
            )

    updated = UpdateUser(
        db,
        current_username=target,
        username=user_data.username,
        phone_number=user_data.phone_number,
        password=user_data.password,
        balance=user_data.balance,
        is_active=user_data.is_active,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update.",
        )

    username = user_data.username or target
    return GetUser(db).get_user_by_username(username)


@admin.delete("/delete")
def delete_user(
    username: str | None = None,
    phone_number: str | None = None,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):

    if not current_user.is_admin:
        raise NotAdminError("Only admins can delete users.")

    deleter = DeleteUser(username=username, phone_number=phone_number, db=db)
    if username:
        deleted = deleter.delete_by_username()
    elif phone_number:
        deleted = deleter.delete_by_phone_number()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username or phone_number is required.",
        )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return {"detail": "User deleted."}


@auth.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    active = GetSession(db).get_session_by_user_id(current_user.id)
    if active is None:
        return {"detail": "No active session.", "ended": False, "session": None}
    ended = end_session(db, active.id, acted_by=current_user)
    return {
        "detail": "Logged out.",
        "ended": True,
        "session": SessionResponse.model_validate(ended),
    }


@auth.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: Customer = Depends(get_current_user)):
    return current_user
