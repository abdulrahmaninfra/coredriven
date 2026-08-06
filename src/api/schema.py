from pydantic import BaseModel, ConfigDict
from typing import Optional

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
    username: Optional[str] | None = None
    phone_number: Optional[str] | None = None
    password: Optional[str] | None = None
    balance: Optional[float] | None = None
    is_active: Optional[bool] | None = None


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
