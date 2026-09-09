from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.api.schema import SessionResponse, SessionStart
from src.core.security import get_current_user
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.exceptions import NotYourSessionError
from src.database.sessions.end import end_session
from src.database.sessions.read import GetSession
from src.database.sessions.start import start_session

sessions = APIRouter(prefix="/sessions", tags=["Sessions"])

VALID_STATUSES = ("active", "ended")


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
    return end_session(db, session_id, acted_by=current_user)


@sessions.get("", response_model=list[SessionResponse])
def list_sessions(
    user_id: str | None = None,
    workstation_id: str | None = None,
    status_filter: str | None = Query(default=None, alias="status"),
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    if status_filter is not None and status_filter not in VALID_STATUSES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status '{status_filter}'. Must be one of: {', '.join(VALID_STATUSES)}.",
        )
    if not current_user.is_admin:
        if user_id is not None and user_id != current_user.id:
            raise NotYourSessionError("You can only list your own sessions.")
        user_id = current_user.id
    return GetSession(db).get_session(
        user_id=user_id, workstation_id=workstation_id, status=status_filter
    )


@sessions.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    session = GetSession(db).get_session_by_id(session_id)
    if session.user_id != current_user.id and not current_user.is_admin:
        raise NotYourSessionError("You are not authorized to view this session.")
    return session
