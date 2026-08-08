
from pydantic import BaseModel, ConfigDict


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


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
