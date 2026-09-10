from sqlalchemy.orm import Session

from src.database.transactions.models import Transactions


class GetTransactions:
    def __init__(self, db: Session):
        self.db = db

    def all(self):
        return (
            self.db.query(Transactions)
            .order_by(Transactions.created_at.desc())
            .all()
        )

    def for_user(self, user_id: str):
        return (
            self.db.query(Transactions)
            .filter(Transactions.user_id == user_id)
            .order_by(Transactions.created_at.desc())
            .all()
        )