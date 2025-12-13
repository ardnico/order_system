import os
from sqlmodel import SQLModel, create_engine, Session


def _default_sqlite_url() -> str:
    data_dir = "/data"
    if os.path.isdir(data_dir):
        return f"sqlite:////{os.path.join(data_dir.lstrip('/'), 'order_system.db')}"
    return "sqlite:///order_system.db"


DATABASE_URL = os.getenv("DATABASE_URL", _default_sqlite_url())
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)


def get_session():
    with Session(engine) as session:
        yield session


def init_db():
    SQLModel.metadata.create_all(engine)
