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
def client() -> TestClient:
    app_client = _build_app()
    token = _signup_login(app_client, "A", "a@x.com")
    app_client.headers.update({"Authorization": f"Bearer {token}"})
    return app_client


@pytest.fixture()
def booking(client) -> dict:
    db = _TestingSession()
    try:
        offering = db.query(Offering).order_by(Offering.id).first()
        assert offering is not None
        centre_id, test_id = offering.centre_id, offering.test_id
    finally:
        db.close()
    good = {
        "centre_id": centre_id,
        "test_id": test_id,
        "appointment_datetime": "2030-01-01T10:00:00Z",
    }
    r = client.post("/bookings/", json=good)
    assert r.status_code == 201
    return r.json()


def test_webhook_idempotent(client, booking):
    payload = {
        "event_id": "evt-1",
        "provider_reference": "ref-1",
        "status": "SUCCESS",
        "booking_id": booking["id"],
    }
    assert client.post("/payments/webhook/", json=payload).status_code == 200
    again = client.post("/payments/webhook/", json=payload)
    assert again.status_code == 200
    # no duplicate payment, still CONFIRMED
    detail = client.get(f"/bookings/{booking['id']}/")
    assert detail.status_code == 200
    assert detail.json()["status"] == "CONFIRMED"
    # same reference + new event_id -> no second row (still single payment effect)
    third = client.post(
        "/payments/webhook/",
        json={
            "event_id": "evt-2",
            "provider_reference": "ref-1",
            "status": "SUCCESS",
            "booking_id": booking["id"],
        },
    )
    assert third.status_code == 200
    detail2 = client.get(f"/bookings/{booking['id']}/")
    assert detail2.json()["status"] == "CONFIRMED"
    # row-level idempotency: exactly one payment row per reference, one event per id
    from app.models.payment import Payment
    from app.models.webhook_event import WebhookEvent

    db = _TestingSession()
    try:
        assert db.query(Payment).filter(Payment.provider_reference == "ref-1").count() == 1
        assert db.query(WebhookEvent).filter(WebhookEvent.event_id == "evt-1").count() == 1
        assert db.query(WebhookEvent).filter(WebhookEvent.event_id == "evt-2").count() == 1
    finally:
        db.close()


def test_webhook_same_reference_new_event_no_dup(client, booking):
    p1 = {
        "event_id": "evt-a",
        "provider_reference": "ref-dup",
        "status": "SUCCESS",
        "booking_id": booking["id"],
    }
    p2 = {
        "event_id": "evt-b",
        "provider_reference": "ref-dup",
        "status": "SUCCESS",
        "booking_id": booking["id"],
    }
    assert client.post("/payments/webhook/", json=p1).status_code == 200
    assert client.post("/payments/webhook/", json=p2).status_code == 200
    detail = client.get(f"/bookings/{booking['id']}/")
    assert detail.json()["status"] == "CONFIRMED"


def test_webhook_confirmed_failed_stays_confirmed(client, booking):
    ok = {
        "event_id": "evt-ok",
        "provider_reference": "ref-ok",
        "status": "SUCCESS",
        "booking_id": booking["id"],
    }
    assert client.post("/payments/webhook/", json=ok).status_code == 200
    bad = {
        "event_id": "evt-bad",
        "provider_reference": "ref-bad",
        "status": "FAILED",
        "booking_id": booking["id"],
    }
    assert client.post("/payments/webhook/", json=bad).status_code == 200
    detail = client.get(f"/bookings/{booking['id']}/")
    assert detail.json()["status"] == "CONFIRMED"


def test_webhook_cancelled_no_transition(client, booking):
    assert client.patch(f"/bookings/{booking['id']}/cancel/").status_code == 200
    payload = {
        "event_id": "evt-c",
        "provider_reference": "ref-c",
        "status": "SUCCESS",
        "booking_id": booking["id"],
    }
    assert client.post("/payments/webhook/", json=payload).status_code == 200
    detail = client.get(f"/bookings/{booking['id']}/")
    assert detail.json()["status"] == "CANCELLED"


def test_webhook_concurrent_duplicate_returns_200(tmp_path):
    """Two in-flight deliveries of the same event_id must both ack 200
    with a single payment row and a single event row (I2 race hardening)."""
    import threading

    from app.models.payment import Payment
    from app.models.webhook_event import WebhookEvent

    db_file = tmp_path / "race.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    with engine.begin() as conn:
        conn.exec_driver_sql("PRAGMA journal_mode=WAL")
    Base.metadata.create_all(bind=engine)
    RaceSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    db = RaceSession()
    try:
        seed_db(db)
        db.commit()
        offering = db.query(Offering).order_by(Offering.id).first()
        assert offering is not None
        centre_id, test_id = offering.centre_id, offering.test_id
    finally:
        db.close()
    app = create_app()

    def _override():
        db = RaceSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override
    race_client = TestClient(app)
    token = _signup_login(race_client, "R", "race@x.com")
    race_client.headers.update({"Authorization": f"Bearer {token}"})
    r = race_client.post(
        "/bookings/",
        json={
            "centre_id": centre_id,
            "test_id": test_id,
            "appointment_datetime": "2030-01-01T10:00:00Z",
        },
    )
    assert r.status_code == 201
    booking_id = r.json()["id"]

    payload = {
        "event_id": "evt-race",
        "provider_reference": "ref-race",
        "status": "SUCCESS",
        "booking_id": booking_id,
    }
    barrier = threading.Barrier(2)
    results: list = []

    def _hit():
        barrier.wait(timeout=15)
        results.append(race_client.post("/payments/webhook/", json=payload))

    threads = [threading.Thread(target=_hit) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=60)

    assert len(results) == 2
    assert all(resp.status_code == 200 for resp in results), [
        (resp.status_code, resp.text) for resp in results
    ]
    db = RaceSession()
    try:
        assert (
            db.query(Payment).filter(Payment.provider_reference == "ref-race").count() == 1
        )
        assert db.query(WebhookEvent).filter(WebhookEvent.event_id == "evt-race").count() == 1
    finally:
        db.close()


def test_webhook_blank_ids_rejected(client, booking):
    blank_event = {
        "event_id": "   ",
        "provider_reference": "ref-blank-1",
        "status": "SUCCESS",
        "booking_id": booking["id"],
    }
    assert client.post("/payments/webhook/", json=blank_event).status_code in (400, 422)
    blank_ref = {
        "event_id": "evt-blank-1",
        "provider_reference": "",
        "status": "SUCCESS",
        "booking_id": booking["id"],
    }
    assert client.post("/payments/webhook/", json=blank_ref).status_code in (400, 422)
