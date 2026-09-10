from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from src.core.config import get_settings

settings = get_settings()

_SQLALCHEMY_DIALECTS = (
    "sqlite",
    "postgres",
    "mysql",
    "mariadb",
    "mssql",
    "oracle",
    "cockroachdb",
)


def _resolve_database_url() -> str:
    url = settings.DATABASE_URL
    if url.startswith(_SQLALCHEMY_DIALECTS):
        return url
    return f"sqlite:///{settings.DATABASE_NAME}"


connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(_resolve_database_url(), connect_args=connect_args)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


def create_db():
    import src.database.customers.models as customer_models  # noqa: F401
    import src.database.sessions.models as session_models  # noqa: F401
    import src.database.transactions.models as transaction_models  # noqa: F401
    import src.database.workstations.models as workstation_models  # noqa: F401
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
