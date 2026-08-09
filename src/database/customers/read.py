from sqlalchemy.orm import Session

from src.database.customers.models import Customer


class GetUser:
    def __init__(self, db: Session):
        self.db = db

    def get_all_users(self):
        return self.db.query(Customer).all()

    def get_user_by_username(self, username: str):
        return self.db.query(Customer).filter(Customer.username == username).first()

    def get_user_by_phone_number(self, phone_number: str):
        return self.db.query(Customer).filter(Customer.phone_number == phone_number).first()

    def get_user(self, username: str | None = None, phone_number: str | None = None):
        query = self.db.query(Customer)

        if username is not None:
            query = query.filter(Customer.username.like(f"%{username}%"))

        if phone_number is not None:
            query = query.filter(Customer.phone_number.like(f"%{phone_number}%"))

        return query.all()
