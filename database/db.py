from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker

from config.settings import DATABASE_URL
from database.models import Base


_engine: Optional[Engine] = None
_SessionLocal: Optional[sessionmaker] = None


def get_engine() -> Engine:
    global _engine

    if _engine is None:
        if not DATABASE_URL:
            raise RuntimeError("DATABASE_URL не задан в переменных окружения.")
        _engine = create_engine(DATABASE_URL, echo=False)

    return _engine


def get_sessionmaker() -> sessionmaker:
    global _SessionLocal

    if _SessionLocal is None:
        _SessionLocal = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
        )

    return _SessionLocal


def init_db() -> None:
    Base.metadata.create_all(bind=get_engine())


def get_session():
    return get_sessionmaker()()
