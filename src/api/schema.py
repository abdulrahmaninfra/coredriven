from datetime import datetime
from src.database.transactions.models import Transactions
from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    username: str
    password: str
    phone_number: str
    balance: float = 0.0


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    username: str
    phone_number: str
    balance: float


class UserUpdate(BaseModel):
    username: str | None = None
    phone_number: str | None = None
    password: str | None = None
    balance: float | None = None
    is_active: bool | None = None
    # Admin-only: which user to update. Defaults to the caller.
    target_username: str | None = None

class UserSelfUpdate(BaseModel):
    phone_number: str | None = None
    password: str | None = None

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class SessionStart(BaseModel):
    workstation_id: str


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    workstation_id: str
    cost: float | None
    start_time: datetime
    end_time: datetime | None
    status: str


class WorkstationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    status: str
    hourly_rate: float
    is_active: bool


class WorkstationCreate(BaseModel):
    name: str
    hourly_rate: float = 0.0
    is_active: bool = True

class WorkstationUpdate(BaseModel):
    name: str | None = None
    hourly_rate: float | None = None
    is_active: bool | None = None

class TransactionResponse(BaseModel):
    """Raw ledger row as stored in the transactions table."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    amount: float
    balance_after: float
    note: str | None
    created_at: datetime

class TransactionMove(BaseModel):
    """Body for the cash-counter operations (admin-only endpoints)."""

    # Cash moves always target a customer account.
    target_username: str
    # Zero, negative, or non-finite amounts are rejected (422) by Pydantic
    # before they reach the database layer.
    amount: float = Field(gt=0)
    note: str | None = None


class TransactionResult(BaseModel):
    """Recharge/deduct answer: the ledger row plus the new balance."""

    transaction: TransactionResponse
    username: str
    new_balance: float


class TransactionListItem(BaseModel):
    """Ledger entry as shown in history views (username resolved)."""

    id: str
    username: str
    amount: float
    balance_after: float
    note: str | None
    created_at: datetime