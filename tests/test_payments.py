import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.main import create_app
from app.models.offering import Offering
from app.seed import seed_db

_engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
_TestingSession = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def _build_app() -> TestClient:
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


def _signup_login(client: TestClient, name: str, email: str, password: str = "secret123") -> str:
    assert client.post(
        "/auth/signup/", json={"name": name, "email": email, "password": password}
    ).status_code in (200, 201)
    r = client.post("/auth/login/", data={"username": email, "password": password})
    assert r.status_code == 200
    return r.json()["access_token"]


@pytest.fixture()
def auth_client() -> TestClient:
    client = _build_app()
    token = _signup_login(client, "A", "a@x.com")
    client.headers.update({"Authorization": f"Bearer {token}"})
    return client


@pytest.fixture()
def seed_ids() -> dict[str, int]:
    db = _TestingSession()
    try:
        offering = db.query(Offering).order_by(Offering.id).first()
        assert offering is not None
        return {"centre_id": offering.centre_id, "test_id": offering.test_id}
    finally:
        db.close()


@pytest.fixture()
def booking(auth_client, seed_ids) -> dict:
    good = {
        "centre_id": seed_ids["centre_id"],
        "test_id": seed_ids["test_id"],
        "appointment_datetime": "2030-01-01T10:00:00Z",
    }
    r = auth_client.post("/bookings/", json=good)
    assert r.status_code == 201
    return r.json()


def test_payment_success_fail_and_reject(auth_client, booking):
    r = auth_client.post("/payments/", json={"booking_id": booking["id"], "simulate": "success"})
    assert r.status_code == 200 and r.json()["booking_status"] == "CONFIRMED"
    r2 = auth_client.post("/payments/", json={"booking_id": booking["id"], "simulate": "success"})
    assert r2.status_code in (400, 409)


def test_payment_failed_path(auth_client, seed_ids):
    good = {
        "centre_id": seed_ids["centre_id"],
        "test_id": seed_ids["test_id"],
        "appointment_datetime": "2030-02-01T10:00:00Z",
    }
    r = auth_client.post("/bookings/", json=good)
    assert r.status_code == 201
    bid = r.json()["id"]
    p = auth_client.post("/payments/", json={"booking_id": bid, "simulate": "fail"})
    assert p.status_code == 200
    assert p.json()["booking_status"] == "FAILED"
    assert p.json()["payment"]["status"] == "FAILED"


def test_payment_cancelled_reject(auth_client, booking):
    assert auth_client.patch(f"/bookings/{booking['id']}/cancel/").status_code == 200
    r = auth_client.post("/payments/", json={"booking_id": booking["id"], "simulate": "success"})
    assert r.status_code in (400, 409)


def test_payment_owner_only(auth_client, booking, seed_ids):
    token2 = _signup_login(auth_client, "B", "b@x.com")
    other = {"Authorization": f"Bearer {token2}"}
    r = auth_client.post(
        "/payments/", json={"booking_id": booking["id"], "simulate": "success"}, headers=other
    )
    assert r.status_code == 403


@pytest.fixture(autouse=True)
def _no_mock_delay(monkeypatch):
    # The 2s provider window is verified live; keep the suite fast.
    monkeypatch.setattr("app.services.payment_service.MOCK_PROCESSING_SECONDS", 0.0)


def test_mock_charge_success_path(monkeypatch, auth_client, booking):
    monkeypatch.setattr("app.services.payment_service.MOCK_SUCCESS_RATE", 1.0)
    r = auth_client.post("/payments/mock/charge", json={"booking_id": booking["id"]})
    assert r.status_code == 200
    body = r.json()
    assert body["outcome"] == "SUCCESS"
    assert body["booking_status"] == "CONFIRMED"
    assert body["event_id"].startswith("mock-")
    assert body["provider_reference"].startswith("mock-")
    from app.models.webhook_event import WebhookEvent

    db = _TestingSession()
    try:
        assert (
            db.query(WebhookEvent).filter(WebhookEvent.event_id == body["event_id"]).count()
            == 1
        )
    finally:
        db.close()


def test_mock_charge_failure_path(monkeypatch, auth_client, booking):
    monkeypatch.setattr("app.services.payment_service.MOCK_SUCCESS_RATE", 0.0)
    r = auth_client.post("/payments/mock/charge", json={"booking_id": booking["id"]})
    assert r.status_code == 200
    assert r.json()["outcome"] == "FAILED"
    assert r.json()["booking_status"] == "FAILED"


def test_mock_charge_rejects_cancelled(monkeypatch, auth_client, booking):
    monkeypatch.setattr("app.services.payment_service.MOCK_SUCCESS_RATE", 1.0)
    assert auth_client.patch(f"/bookings/{booking['id']}/cancel/").status_code == 200
    r = auth_client.post("/payments/mock/charge", json={"booking_id": booking["id"]})
    assert r.status_code in (400, 409)


def test_mock_charge_twice_second_rejected(monkeypatch, auth_client, booking):
    monkeypatch.setattr("app.services.payment_service.MOCK_SUCCESS_RATE", 1.0)
    first = auth_client.post("/payments/mock/charge", json={"booking_id": booking["id"]})
    assert first.status_code == 200
    assert first.json()["outcome"] == "SUCCESS"
    second = auth_client.post("/payments/mock/charge", json={"booking_id": booking["id"]})
    assert second.status_code == 409
