from sqlalchemy.orm import Session

from src.database.workstations.models import Workstation


class GetWorkstation:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self):
        return self.db.query(Workstation).all()

    def get_by_id(self, workstation_id: str):
        return self.db.query(Workstation).filter(Workstation.id == workstation_id).first()
