from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.api.schema import SessionResponse, Token, UserResponse, UserSelfUpdate
from src.core.security import create_access_token, get_current_user, verify_password
from src.database.customers.database import get_db
from src.database.customers.models import Customer
from src.database.customers.read import GetUser
from src.database.customers.update import UpdateUser
from src.database.sessions.end import end_session
from src.database.sessions.read import GetSession

auth = APIRouter(prefix="/auth", tags=["Authentication"])


@auth.post("/login", response_model=Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = GetUser(db).get_user_by_username(form_data.username)

    if user is None or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated.",
        )

    access_token = create_access_token(data={"sub": user.username})
    return Token(access_token=access_token)


@auth.put("/me", response_model=UserResponse)
def update_self(
    user_data: UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    updated = UpdateUser(
        db,
        current_username=current_user.username,
        phone_number=user_data.phone_number,
        password=user_data.password,
    )

    if not updated:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields provided to update.",
        )

    return GetUser(db).get_user_by_username(current_user.username)


@auth.post("/logout")
def logout(
    db: Session = Depends(get_db),
    current_user: Customer = Depends(get_current_user),
):
    active = GetSession(db).get_session_by_user_id(current_user.id)
    if active is None:
        return {"detail": "No active session.", "ended": False, "session": None}
    ended = end_session(db, active.id, acted_by=current_user)
    return {
        "detail": "Logged out.",
        "ended": True,
        "session": SessionResponse.model_validate(ended),
    }


@auth.get("/me", response_model=UserResponse)
def read_users_me(current_user: Customer = Depends(get_current_user)):
    return current_user
