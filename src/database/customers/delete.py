from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.database.customers.models import Customer


class DeleteUser:
    def __init__(self, username: str | None, phone_number: str | None, db: Session):
        self.db = db
        self.username = username
        self.phone_number = phone_number

    def delete_by_phone_number(self):
        if self.phone_number is None:
            print("Phone number is required")
            return False
        try:
            deleted = (
                self.db.query(Customer)
                .filter(Customer.phone_number == self.phone_number)
                .delete()
            )
            self.db.commit()
            return deleted > 0

        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            self.db.rollback()
            return False

    def delete_by_username(self):
        if self.username is None:
            print("Username is required")
            return False
        try:
            deleted = (
                self.db.query(Customer)
                .filter(Customer.username == self.username)
                .delete()
            )
            self.db.commit()
            return deleted > 0

        except SQLAlchemyError as e:
            print(f"Database error: {e}")
            self.db.rollback()
            return False