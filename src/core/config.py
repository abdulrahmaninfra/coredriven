import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    API_TITLE: str = ""
    API_DESCRIPTION: str = ""
    API_VERSION: str = ""

    DATABASE_URL: str = ""
    DATABASE_NAME: str


    HOST: str
    PORT: int 


    JWT_ALGORITHM: str
    PASSWORD_HASH_SECRET_KEY: str
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int

    # ALLOWED_ORIGINS: list[str] = [
    #     f"localhost:{os.getenv('PORT')}",
    #     f"127.0.0.1:{os.getenv('PORT')}",
    # ]
    # ALLOWED_METHODS: list[str] = ["GET", "POST", "PUT", "DELETE"]




@lru_cache
def get_settings() -> Settings:
    return Settings()
