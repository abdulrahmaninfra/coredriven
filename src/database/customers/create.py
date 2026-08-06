import uuid

from sqlalchemy.orm import Session

from src.core.security import hash_password
from src.database.customers.models import Customer


class CreateNewUser:
    def __init__(self, username: str, password: str, phone_number: str, balance: float):
        self.id = str(uuid.uuid4())
        self.username = username
        self.password = hash_password(password)
        self.phone_number = phone_number
        self.balance = balance

    def create_user(self, db: Session):
        customer = Customer(
            id=self.id,
            username=self.username,
            password_hash=self.password,
            balance=self.balance,
            phone_number=self.phone_number,
        )
        db.add(customer)
        db.commit()
        db.refresh(customer)
        return customer
