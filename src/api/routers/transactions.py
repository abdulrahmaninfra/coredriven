from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.schema import (
    TransactionListItem,
    TransactionMove,
    TransactionResponse,
    TransactionResult,
)
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.exceptions import NotAdminError
from src.database.transactions.create import deduct, recharge
from src.database.transactions.models import Transactions
from src.database.transactions.read import GetTransactions

transactions = APIRouter(prefix="/transactions", tags=["Transactions"])


def _require_admin(current_user: Customer) -> None:
    if not current_user.is_admin:
        raise NotAdminError("Only admins can manage transactions.")


def _with_usernames(db: Session, rows: list[Transactions]) -> list[TransactionListItem]:
    ids = {row.user_id for row in rows}
    names: dict[str, str] = {}
    if ids:
        for user in db.query(Customer).filter(Customer.id.in_(ids)).all():
            names[user.id] = user.username
    return [
        TransactionListItem(
            id=row.id,
            username=names.get(row.user_id, row.user_id),
            amount=float(row.amount),
            balance_after=float(row.balance_after),
            note=row.note,
            created_at=row.created_at,
        )
        for row in rows
    ]


@transactions.post(
    "/recharge", response_model=TransactionResult, status_code=status.HTTP_201_CREATED
)
def recharge_balance(
    payload: TransactionMove,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    row = recharge(db, payload.target_username, payload.amount, payload.note)
    return TransactionResult(
        transaction=TransactionResponse.model_validate(row),
        username=payload.target_username,
        new_balance=float(row.balance_after),
    )


@transactions.post(
    "/deduct", response_model=TransactionResult, status_code=status.HTTP_201_CREATED
)
def deduct_balance(
    payload: TransactionMove,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    row = deduct(db, payload.target_username, payload.amount, payload.note)
    return TransactionResult(
        transaction=TransactionResponse.model_validate(row),
        username=payload.target_username,
        new_balance=float(row.balance_after),
    )


@transactions.get("", response_model=list[TransactionListItem])
def list_transactions(
    username: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)

    query = GetTransactions(db)
    rows = query.for_user(username) if username else query.all()
    return _with_usernames(db, rows[:limit])
