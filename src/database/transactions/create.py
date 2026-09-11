import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.customers.models import Customer
from src.database.exceptions import InsufficientBalanceError, UserNotFoundError
from src.database.transactions.models import Transactions


def _get_user(db: Session, username: str) -> Customer:
    user = db.execute(
        select(Customer).where(Customer.username == username).with_for_update()
    ).scalar_one_or_none()

    if not user:
        raise UserNotFoundError(f"User '{username}' not found.")

    return user


def _apply(
    db: Session,
    user: Customer,
    signed_amount: float,
    note: str | None,
) -> Transactions:
    current = float(user.balance)
    new_balance = round(current + signed_amount, 2)

    if new_balance < 0:
        raise InsufficientBalanceError(
            f"Insufficient balance: cannot move {-signed_amount} "
            f"from balance {current}."
        )

    row = Transactions(
        id=str(uuid.uuid4()),
        user_id=user.id,
        amount=round(signed_amount, 2),
        balance_after=new_balance,
        note=note,
    )

    user.balance = new_balance
    db.add(row)

    return row


def _move(
    db: Session,
    username: str,
    signed_amount: float,
    note: str | None,
) -> Transactions:
    try:
        with db.begin():
            user = _get_user(db, username)
            row = _apply(db, user, signed_amount, note)

        db.refresh(row)
        return row

    except Exception:
        db.rollback()
        raise


def recharge(
    db: Session,
    username: str,
    amount: float,
    note: str | None = None,
) -> Transactions:
    return _move(db, username, amount, note)


def deduct(
    db: Session,
    username: str,
    amount: float,
    note: str | None = None,
) -> Transactions:
    return _move(db, username, -amount, note)
