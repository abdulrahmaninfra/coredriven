from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.api.schema import SessionResponse, SessionStart
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.sessions.end import end_session
from src.database.sessions.read import GetSession
from src.database.sessions.start import start_session

sessions = APIRouter(prefix="/sessions", tags=["Sessions"])


@sessions.post("/start", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start(
    payload: SessionStart,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    return start_session(db, current_user.id, payload.workstation_id)


@sessions.post("/{session_id}/end", response_model=SessionResponse)
def end(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    return end_session(db, session_id)


@sessions.get("", response_model=list[SessionResponse])
def list_sessions(
    user_id: str | None = None,
    workstation_id: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    return GetSession(db).get_session(
        user_id=user_id, workstation_id=workstation_id, status=status
    )


@sessions.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    return GetSession(db).get_session_by_id(session_id)
