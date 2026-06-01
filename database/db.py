from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from config.settings import DATABASE_URL


engine = create_engine(DATABASE_URL, echo=False)

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False
)


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    return SessionLocal()