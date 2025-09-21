from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from .config import settings


class Base(DeclarativeBase):
    pass


# For SQLite, enable check_same_thread=False for multithreaded FastAPI
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {},
    echo=False,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db():
    from . import models  # noqa: F401 - ensure models are imported for metadata
    Base.metadata.create_all(bind=engine)


