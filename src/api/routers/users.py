import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.schema import UserCreate, UserResponse, UserUpdate
from src.core.security import get_current_user
from src.database.customers.create import CreateNewUser
from src.database.customers.database import get_db
from src.database.customers.delete import DeleteUser
from src.database.customers.models import Customer
from src.database.customers.read import GetUser
from src.database.customers.update import UpdateUser
from src.database.exceptions import NotAdminError, UserNotFoundError

logger = logging.getLogger(__name__)

users = APIRouter(prefix="/users", tags=["Users"])


@users.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user",
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


@users.get("", response_model=list[UserResponse], summary="List users")
def list_users(
    username: str | None = None,
    phone_number: str | None = None,
    user_id: str | None = None,
    is_active: bool | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise NotAdminError("Only admins can list users.")

    return GetUser(db).get_user(
        username=username,
        phone_number=phone_number,
        user_id=user_id,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )


@users.put("/{user_id}", response_model=UserResponse, summary="Update user by ID")
def update_user(
    user_id: str,
    user_data: UserUpdate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    if not current_user.is_admin:
        raise NotAdminError("Only admins can update user information.")

    target = GetUser(db).get_by_identifier(user_id)
    if target is None:
        raise UserNotFoundError(f"User '{user_id}' not found.")

    if user_data.username is not None and user_data.username != target.username:
        existing = GetUser(db).get_user_by_username(user_data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Username '{user_data.username}' is already taken.",
            )

    updated = UpdateUser(
        db,
        user_id=target.id,
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

    return GetUser(db).get_user_by_id(target.id)


@users.delete("/{user_id}", summary="Delete user by ID")
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):

    if not current_user.is_admin:
        raise NotAdminError("Only admins can delete users.")

    target = GetUser(db).get_by_identifier(user_id)
    if target is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    deleted = DeleteUser(db=db, user_id=target.id).delete_by_id()

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    return {"detail": "User deleted."}
