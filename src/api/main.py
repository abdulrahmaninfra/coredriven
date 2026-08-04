import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException

from src.api.schema import UserCreate, UserResponse
from src.database.customers.connect import create_db, get_db_connection
from src.database.customers.create import CreateNewUser


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
