import uuid

from sqlalchemy.orm import Session

from src.database.customers.models import Customer
from src.database.exceptions import InsufficientBalanceError, UserNotFoundError
from src.database.transactions.models import Transactions


def _get_user(db: Session, username: str) -> Customer:
    user = db.query(Customer).filter(Customer.username == username).first()
    if not user:
        raise UserNotFoundError(f"User '{username}' not found.")
    return user


def _apply(
    db: Session, user: Customer, signed_amount: float, note: str | None
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
    db.commit()
    db.refresh(row)
    return row


def recharge(
    db: Session, username: str, amount: float, note: str | None = None
) -> Transactions:
    return _apply(db, _get_user(db, username), amount, note)


def deduct(
    db: Session, username: str, amount: float, note: str | None = None
) -> Transactions:
    return _apply(db, _get_user(db, username), -amount, note)
