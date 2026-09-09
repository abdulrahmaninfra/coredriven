from sqlalchemy.orm import Session

from src.database.customers.models import Customer
from src.database.exceptions import WorkstationNotFoundError
from src.database.sessions.end import end_session
from src.database.sessions.read import GetSession
from src.database.workstations.read import GetWorkstation


class DeleteWorkstation:
    def __init__(self, db: Session):
        self.db = db

    def delete_by_name(self, name: str, acted_by: Customer) -> str | None:

        workstation = GetWorkstation(self.db).get_by_name(name)
        if workstation is None:
            raise WorkstationNotFoundError(f"Workstation '{name}' not found.")

        active = GetSession(self.db).get_session_by_workstation_id(workstation.id)
        ended_session_id = None
        if active is not None:
            ended = end_session(self.db, active.id, acted_by=acted_by)
            ended_session_id = ended.id

        self.db.delete(workstation)
        self.db.commit()
        return ended_session_id
