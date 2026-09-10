import logging
import math

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.api.schema import UserCharge, UserResponse
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.customers.read import GetUser
from src.database.exceptions import (
    InsufficientBalanceError,
    NotAdminError,
    UserNotFoundError,
)

logger = logging.getLogger(__name__)

charge = APIRouter(prefix="/charge", tags=["Top Up & Deduct"])


@charge.put("/charge", response_model=UserResponse)
def charge_user(
    user_data: UserCharge,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):

    if not current_user.is_admin:
        raise NotAdminError("Only admins can update user balance.")

    if not math.isfinite(user_data.amount) or user_data.amount == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Amount must be a finite, non-zero number.",
        )

    target = user_data.target_username or current_user.username
    user = GetUser(db).get_user_by_username(target)
    if user is None:
        raise UserNotFoundError(f"User '{target}' not found.")

    new_balance = round(float(user.balance) + float(user_data.amount), 2)
    if new_balance < 0:
        raise InsufficientBalanceError(
            f"Insufficient balance: cannot deduct {abs(user_data.amount)} "
            f"from balance {float(user.balance)}."
        )

    user.balance = new_balance
    db.commit()
    db.refresh(user)
    logger.info(
        "Admin '%s' charged user '%s' by %s (new balance %s)",
        current_user.username,
        target,
        user_data.amount,
        new_balance,
    )
    return user
