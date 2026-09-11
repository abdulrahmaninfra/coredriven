import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.api.schema import (
    AdminPermissionResponse,
    UserAdminResponse,
    UserAdminUpdate,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from src.core.permissions import is_superadmin, require_permission
from src.core.security import get_current_user
from src.database.customers.create import CreateNewUser
from src.database.customers.database import get_db
from src.database.customers.delete import DeleteUser
from src.database.customers.models import Customer
from src.database.customers.permissions.crud import (
    delete_for_customer,
    ensure_for_customer,
    get_for_customer,
    set_flags,
)
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
    require_permission(current_user, "can_manage_users", "register new users.")

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
    require_permission(current_user, "can_manage_users", "list users.")

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
    require_permission(current_user, "can_manage_users", "update user information.")

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
    require_permission(current_user, "can_manage_users", "delete users.")

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


@users.get(
    "/{user_id}/permissions",
    response_model=AdminPermissionResponse,
    summary="Get admin permissions",
)
def get_admin_permissions(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    require_permission(current_user, "can_manage_admins", "view admin permissions.")

    target = GetUser(db).get_by_identifier(user_id)
    if target is None:
        raise UserNotFoundError(f"User '{user_id}' not found.")

    row = get_for_customer(db, target.id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{target.username}' has no admin permissions.",
        )
    return row


@users.put(
    "/{user_id}/admin",
    response_model=UserAdminResponse,
    summary="Manage admin role and permissions",
)
def manage_admin(
    user_id: str,
    payload: UserAdminUpdate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    require_permission(current_user, "can_manage_admins", "manage admins.")

    target = GetUser(db).get_by_identifier(user_id)
    if target is None:
        raise UserNotFoundError(f"User '{user_id}' not found.")

    caller_super = is_superadmin(current_user)
    if not caller_super:
        if payload.is_superadmin:
            raise NotAdminError("Only superadmins can grant superadmin.")
        if payload.permissions is not None and payload.permissions.can_manage_admins:
            raise NotAdminError("Only superadmins can grant 'can_manage_admins'.")
        if is_superadmin(target):
            raise NotAdminError("Only superadmins can modify a superadmin.")

    if payload.is_admin is not None:
        target.is_admin = payload.is_admin
    if payload.is_superadmin is not None:
        target.is_superadmin = payload.is_superadmin
        if payload.is_superadmin:
            target.is_admin = True

    if not target.is_admin and not target.is_superadmin:
        delete_for_customer(db, target.id)
    else:
        ensure_for_customer(db, target.id)
        if is_superadmin(target):
            set_flags(
                db,
                target.id,
                can_manage_admins=True,
                can_manage_users=True,
                can_manage_workstations=True,
                can_manage_billing=True,
                read_only_billing=False,
            )
        elif payload.permissions is not None:
            set_flags(
                db,
                target.id,
                **payload.permissions.model_dump(exclude_unset=True),
            )

    db.commit()
    db.refresh(target)
    row = get_for_customer(db, target.id)
    return UserAdminResponse(
        id=target.id,
        username=target.username,
        is_admin=target.is_admin,
        is_superadmin=target.is_superadmin,
        permissions=AdminPermissionResponse.model_validate(row) if row else None,
    )
