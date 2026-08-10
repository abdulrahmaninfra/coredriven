import uuid

from sqlalchemy.orm import Session

from src.core.security import hash_password
from src.database.sessions.models import Customer

class CreateNewSession:
    def __init__(self, user_id: str, workstation_id: str):
        self.id = str(uuid.uuid4())
        self.user_id = user_id
        self.workstation_id = workstation_id

    def create_session(self, db: Session):
        session = Customer(
            id=self.id,
            user_id=self.user_id,
            workstation_id=self.workstation_id,
        )
        db.add(session)
        db.commit()
        db.refresh(session)
        return session