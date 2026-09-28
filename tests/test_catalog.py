import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register models on Base.metadata)
from app.core.database import Base, get_db
from app.main import create_app
from app.seed import seed_db

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def seeded_client() -> TestClient:
    Base.metadata.drop_all(bind=_engine)
    Base.metadata.create_all(bind=_engine)
    db = _TestingSession()
    try:
        seed_db(db)
    finally:
        db.close()
    app = create_app()

    def _override():
        db = _TestingSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    return TestClient(app)


def test_catalog_lists_and_detail(seeded_client):
    assert seeded_client.get("/centres/").status_code == 200
    centres = seeded_client.get("/centres/").json()
    assert len(centres) >= 2
    d = seeded_client.get(f"/centres/{centres[0]['id']}/").json()
    assert "tests" in d and "price" in d["tests"][0]
    assert seeded_client.get("/tests/").status_code == 200
    assert seeded_client.get("/centres/999999/").status_code == 404
