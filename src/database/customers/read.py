from sqlalchemy.orm import Session

from src.database.customers.models import Customer


class GetUser:
    def __init__(self, db: Session):
        self.db = db

    def get_all_users(self):
        return self.db.query(Customer).all()

    def get_user_by_username(self, username: str):
        return self.db.query(Customer).filter(Customer.username == username).first()

    def get_user_by_id(self, user_id: str):
        return self.db.query(Customer).filter(Customer.id == user_id).first()

    def get_user_by_phone_number(self, phone_number: str):
        return (
            self.db.query(Customer)
            .filter(Customer.phone_number == phone_number)
            .first()
        )

    def get_by_identifier(self, identifier: str):
        user = self.get_user_by_id(identifier)
        if user is None:
            user = self.get_user_by_username(identifier)
        return user

    def get_user(
        self,
        username: str | None = None,
        phone_number: str | None = None,
        user_id: str | None = None,
        is_active: bool | None = None,
        limit: int | None = None,
        offset: int | None = None,
    ):
        if user_id is not None:
            user = self.get_user_by_id(user_id)
            return [user] if user is not None else []
        query = self.db.query(Customer).order_by(Customer.username)

        if username is not None:
            query = query.filter(Customer.username.like(f"%{username}%"))

        if phone_number is not None:
            query = query.filter(Customer.phone_number.like(f"%{phone_number}%"))

        if is_active is not None:
            query = query.filter(Customer.is_active == is_active)

        if offset is not None:
            query = query.offset(offset)

        if limit is not None:
            query = query.limit(limit)

        return query.all()
