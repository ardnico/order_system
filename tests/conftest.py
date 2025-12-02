import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine

from app import db
from app import models  # ensure models are registered with metadata
from app.main import app


test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False})

def override_get_session():
    with Session(test_engine) as session:
        yield session


def reset_database():
    SQLModel.metadata.drop_all(test_engine)
    SQLModel.metadata.create_all(test_engine)


db.engine = test_engine
app.dependency_overrides[db.get_session] = override_get_session


@pytest.fixture(autouse=True)
def setup_db():
    reset_database()
    yield


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def session():
    with Session(test_engine) as session:
        yield session
