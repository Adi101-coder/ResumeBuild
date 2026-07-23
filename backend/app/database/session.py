from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    echo=settings.sql_echo,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

_db_logger = __import__("logging").getLogger("app.db")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    _db_logger.debug("DB session opened")
    try:
        yield db
    finally:
        db.close()
        _db_logger.debug("DB session closed")
