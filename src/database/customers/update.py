from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.core.security import hash_password as _hash_password
from src.database.customers.models import Customer


def UpdateUser(
    db: Session,
    current_username: str | None = None,
    username: str | None = None,
    phone_number: str | None = None,
    password: str | None = None,
    balance: float | None = None,
    is_active: bool | None = None,
    user_id: str | None = None,
):
    values = {}

    if username is not None:
        values["username"] = username

    if phone_number is not None:
        values["phone_number"] = phone_number

    if password is not None:
        values["password_hash"] = _hash_password(password)

    if balance is not None:
        values["balance"] = balance

    if is_active is not None:
        values["is_active"] = is_active

    if not values:
        print("No fields to update")
        return False

    try:
        query = db.query(Customer)
        if user_id is not None:
            query = query.filter(Customer.id == user_id)
        elif current_username is not None:
            query = query.filter(Customer.username == current_username)
        else:
            print("No user identifier provided")
            return False
        result = query.update(values)
        db.commit()
        return result > 0

    except SQLAlchemyError as e:
        print(f"Database error: {e}")
        db.rollback()
        return False
