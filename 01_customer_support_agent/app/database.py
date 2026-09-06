from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.settings import SETTINGS

DATABASE_URL = SETTINGS.database_url

engine_options: dict = {"pool_pre_ping": True}
if DATABASE_URL.startswith("sqlite"):
    engine_options["connect_args"] = {"check_same_thread": False}
else:
    engine_options.update(
        pool_size=SETTINGS.db_pool_size,
        max_overflow=SETTINGS.db_max_overflow,
        pool_timeout=SETTINGS.db_pool_timeout_seconds,
        pool_recycle=SETTINGS.db_pool_recycle_seconds,
        connect_args={"connect_timeout": SETTINGS.db_pool_timeout_seconds},
    )

engine = create_engine(DATABASE_URL, **engine_options)
SessionLocal = sessionmaker(
    bind=engine,
    class_=Session,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
