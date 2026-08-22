"""Database initialization helpers."""

from sqlalchemy.engine import Engine

from app.db.base import Base
from app.db.session import engine as default_engine


def init_db(engine: Engine = default_engine) -> None:
    Base.metadata.create_all(bind=engine)
