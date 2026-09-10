from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from src.api.schema import TransactionCreate, TransactionResponse
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.exceptions import NotAdminError
from src.database.transactions.create import deduct, recharge
from src.database.transactions.read import GetTransactions

transactions = APIRouter(prefix="/auth/admin/transactions", tags=["Transactions"])


def _require_admin(current_user: Customer):
    if not current_user.is_admin:
        raise NotAdminError("Only admins can manage transactions.")


@transactions.post(
    "/recharge", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
def recharge_balance(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    return recharge(db, payload.username, payload.amount, payload.note)


@transactions.post(
    "/deduct", response_model=TransactionResponse, status_code=status.HTTP_201_CREATED
)
def deduct_balance(
    payload: TransactionCreate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    return deduct(db, payload.username, payload.amount, payload.note)


@transactions.get("", response_model=list[TransactionResponse])
def list_transactions(
    user_id: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    query = GetTransactions(db)
    if user_id:
        return query.for_user(user_id)[:limit]
    return query.all()[:limit]


@transactions.get("/{user_id}", response_model=list[TransactionResponse])
def get_user_transactions(
    user_id: str,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    _require_admin(current_user)
    return GetTransactions(db).for_user(user_id)[:limit]