from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    API_TITLE: str = "CoreDriven API"
    API_DESCRIPTION: str = "POS and Internet Cafe management"
    API_VERSION: str = "0.1.0"

    DATABASE_NAME: str
    DATABASE_URL: str


    HOST: str
    PORT: int

    JWT_ALGORITHM: str
    PASSWORD_HASH_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    ALLOWED_ORIGINS: list[str] = ["*"]
    ALLOWED_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE"]

    FIRST_SUPERADMIN_EMAIL: str
    FIRST_SUPERADMIN_PASSWORD: str


@lru_cache
def get_settings() -> Settings:
    return Settings()
