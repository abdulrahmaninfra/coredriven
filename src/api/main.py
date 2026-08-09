from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.api.auth import auth as authentication_router
from src.core.config import get_settings
from src.database.customers.database import create_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


def create_auth_application() -> FastAPI:
    settings = get_settings()

    application = FastAPI(
        title=settings.API_TITLE,
        description=settings.API_DESCRIPTION,
        version=settings.API_VERSION,
        lifespan=lifespan,
    )

    application.add_middleware(GZipMiddleware, minimum_size=1000)
    application.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=settings.ALLOWED_METHODS,
        allow_headers=["*"],
        max_age=86400,
    )

    application.include_router(authentication_router)

    return application


auth = create_auth_application()
