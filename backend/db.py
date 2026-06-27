import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

DB_PATH = os.environ.get("APP_DB_PATH", "app_data.db")
ENGINE = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True,
                       connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=ENGINE, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def init_db():
    from backend import models  # noqa: F401  (register models)
    Base.metadata.create_all(ENGINE)


@contextmanager
def get_session():
    s = SessionLocal()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()