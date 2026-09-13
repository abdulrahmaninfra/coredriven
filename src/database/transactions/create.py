import uuid
from decimal import ROUND_HALF_EVEN, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.database.customers.models import Customer
from src.database.exceptions import (
    BalanceOverflowError,
    InsufficientBalanceError,
    UserNotFoundError,
)
from src.database.transactions.models import Transactions

_CENT = Decimal("0.01")
# Matches the Numeric(10, 2) balance column: at most 8 integer digits.
# SQLite silently stores bigger values; Postgres would reject the INSERT,
# so the cap is enforced in business logic on every balance move.
_MAX_BALANCE = Decimal("99999999.99")


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
    signed_amount: Decimal,
    note: str | None,
) -> Transactions:
    signed = signed_amount.quantize(_CENT, rounding=ROUND_HALF_EVEN)
    current = Decimal(str(user.balance))
    new_balance = (current + signed).quantize(_CENT, rounding=ROUND_HALF_EVEN)

    if new_balance < 0:
        raise InsufficientBalanceError(
            f"Insufficient balance: cannot move {-signed} "
            f"from balance {current}."
        )

    if new_balance > _MAX_BALANCE:
        raise BalanceOverflowError(
            f"Balance overflow: {new_balance} would exceed "
            f"the maximum balance of {_MAX_BALANCE}."
        )

    row = Transactions(
        id=str(uuid.uuid4()),
        user_id=user.id,
        amount=signed,
        balance_after=new_balance,
        note=note,
    )

    user.balance = new_balance
    db.add(row)

    return row


def _move(
    db: Session,
    username: str,
    signed_amount: Decimal,
    note: str | None,
) -> Transactions:
    # begin_nested() (SAVEPOINT) instead of begin(): the request session may
    # already hold an autobegun transaction from earlier reads (e.g. the
    # auth lookup in get_current_user), on which begin() would raise
    # "A transaction is already begun on this Session". The savepoint still
    # keeps the balance move all-or-nothing.
    try:
        with db.begin_nested():
            user = _get_user(db, username)
            row = _apply(db, user, signed_amount, note)

        db.commit()
        db.refresh(row)
        return row

    except Exception:
        db.rollback()
        raise


def recharge(
    db: Session,
    username: str,
    amount: Decimal,
    note: str | None = None,
) -> Transactions:
    return _move(db, username, amount, note)


def deduct(
    db: Session,
    username: str,
    amount: Decimal,
    note: str | None = None,
) -> Transactions:
    return _move(db, username, -amount, note)