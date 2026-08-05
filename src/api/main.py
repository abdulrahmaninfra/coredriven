import sqlite3
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware

from src.api import auth
from src.api.schema import UserCreate, UserResponse
from src.database.customers.connect import create_db, get_db_connection
from src.database.customers.create import CreateNewUser
from src.database.customers.read import GetUser
from src.core.security import get_current_user


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


app = FastAPI(
    title="Coredriven",
    description="POS and Internet Cafe Management System",
    version="0.0.1",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Routers ---
app.include_router(auth.router)


# --- Example protected route ---
@app.get("/me", tags=["Customers"])
def get_me(
    current_user: str = Depends(get_current_user),
    conn: sqlite3.Connection = Depends(get_db_connection),
):
    """Returns the profile of the currently logged-in customer."""
    user = GetUser(conn).get_user_by_username(current_user)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    return {
        "username": user["username"],
        "phone_number": user["phone_number"],
        "balance": user["balance"],
    }
