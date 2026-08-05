from pydantic import BaseModel


class UserCreate(BaseModel):
    username: str
    password: str
    phone_number: str
    balance: float = 0.0


class UserResponse(BaseModel):
    username: str
    phone_number: str
    balance: float


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
