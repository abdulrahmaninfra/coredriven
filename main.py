import sys
from contextlib import asynccontextmanager
from pathlib import Path

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[0]))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from src.api.errors import app_error_handler
from src.api.routers.auth import admin as auth_admin_router
from src.api.routers.auth import auth as authentication_router
from src.api.routers.sessions import sessions as sessions_router
from src.api.routers.workstations import workstations as workstations_router
from src.core.config import get_settings
from src.database.customers.database import create_db
from src.database.exceptions import AppError


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db()
    yield


def create_application() -> FastAPI:
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

    application.add_exception_handler(AppError, app_error_handler)

    application.include_router(authentication_router)
    application.include_router(sessions_router)
    application.include_router(workstations_router)
    application.include_router(auth_admin_router)

    return application


app = create_application()


if __name__ == "__main__":
    import uvicorn

    from src.core.config import get_settings

    settings = get_settings()
    uvicorn.run(
        "main:app", host=settings.HOST, port=settings.PORT, reload=True
    )
