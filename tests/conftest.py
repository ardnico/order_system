import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine

from app import db
from app import models  # ensure models are registered with metadata
from app.main import app, ensure_root_admin


test_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

def override_get_session():
    with Session(test_engine) as session:
        yield session


def reset_database():
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)
    ensure_root_admin()


db.engine = test_engine
import app.main as main
main.engine = test_engine
app.dependency_overrides[db.get_session] = override_get_session


@pytest.fixture(autouse=True)
def setup_db():
    reset_database()
    yield


@pytest.fixture
def client():
    reset_database()
    return TestClient(app)


@pytest.fixture
def session():
    with Session(test_engine) as session:
        yield session
