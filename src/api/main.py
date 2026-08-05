import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from src.api.deps import get_current_user
from src.api.schema import Token, UserCreate, UserResponse
from src.core.security import create_access_token, verify_password
from src.database.customers.connect import create_db, get_db_connection
from src.database.customers.create import CreateNewUser
from src.database.customers.read import GetUser


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


app = FastAPI(lifespan=lifespan)

@app.post("/users", response_model=UserResponse)
def create_user(create_new_user: UserCreate, conn: sqlite3.Connection= Depends(get_db_connection)):
    try:
        user_creator = CreateNewUser(
            username=create_new_user.username,
            password=create_new_user.password,
            phone_number=create_new_user.phone_number,
            balance=create_new_user.balance
        )

        new_user = user_creator.create_user(conn)
        return dict(new_user)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/login", response_model=Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), conn: sqlite3.Connection = Depends(get_db_connection)):
    user = GetUser(conn).get_user_by_username(form_data.username)

    if user is None or not verify_password(form_data.password, user["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(data={"sub": user["username"]})
    return Token(access_token=access_token)


@app.get("/users/me", response_model=UserResponse)
def read_users_me(current_user: dict = Depends(get_current_user)):
    return current_user
