from sqlalchemy.orm import Session

from src.database.sessions.models import Sessions


class GetSession:
    def __init__(self, db: Session):
        self.db = db

    def get_all_sessions(self):
        return self.db.query(Sessions).all()

    def get_session_by_user_id(self, user_id: str):
        return (
            self.db.query(Sessions)
            .filter(Sessions.user_id == user_id, Sessions.status == "active")
            .first()
        )

    def get_session_by_workstation_id(self, workstation_id: str):
        return (
            self.db.query(Sessions)
            .filter(Sessions.workstation_id == workstation_id, Sessions.status == "active")
            .first()
        )

    def get_session(self, user_id: str | None = None, workstation_id: str | None = None):
        query = self.db.query(Sessions)

        if user_id is not None:
            query = query.filter(Sessions.user_id == user_id)

        if workstation_id is not None:
            query = query.filter(Sessions.workstation_id == workstation_id)

        return query.all()
