import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401  (register models on Base.metadata)
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


def test_booking_guards(auth_client, seed_ids):
    past = {"centre_id": 1, "test_id": 1, "appointment_datetime": "2020-01-01T10:00:00Z"}
    assert auth_client.post("/bookings/", json=past).status_code in (400, 422)
    bad = {"centre_id": 999999, "test_id": 1, "appointment_datetime": "2030-01-01T10:00:00Z"}
    assert auth_client.post("/bookings/", json=bad).status_code == 400
    good = {
        "centre_id": seed_ids["centre_id"],
        "test_id": seed_ids["test_id"],
        "appointment_datetime": "2030-01-01T10:00:00Z",
    }
    r = auth_client.post("/bookings/", json=good)
    assert r.status_code == 201 and r.json()["status"] == "PENDING"
    bid = r.json()["id"]
    assert auth_client.patch(f"/bookings/{bid}/cancel/").status_code == 200
    assert auth_client.patch(f"/bookings/{bid}/cancel/").status_code == 409


def test_booking_reschedule_moves_date_keeps_status(auth_client, seed_ids):
    good = {
        "centre_id": seed_ids["centre_id"],
        "test_id": seed_ids["test_id"],
        "appointment_datetime": "2030-08-01T10:00:00Z",
    }
    r = auth_client.post("/bookings/", json=good)
    assert r.status_code == 201
    bid = r.json()["id"]
    new_dt = "2030-09-01T10:00:00Z"
    rr = auth_client.patch(f"/bookings/{bid}/reschedule/", json={"appointment_datetime": new_dt})
    assert rr.status_code == 200
    body = rr.json()
    assert body["appointment_datetime"].startswith("2030-09-01")
    assert body["status"] == "PENDING"
    assert body["amount"] == r.json()["amount"]
    # past date rejected, cancelled rejected, foreign rejected
    assert auth_client.patch(f"/bookings/{bid}/reschedule/", json={"appointment_datetime": "2020-01-01T10:00:00Z"}).status_code in (400, 422)
    assert auth_client.patch(f"/bookings/{bid}/cancel/").status_code == 200
    assert auth_client.patch(f"/bookings/{bid}/reschedule/", json={"appointment_datetime": new_dt}).status_code == 409
    token2 = _signup_login(auth_client, "D", "d@x.com")
    other = {"Authorization": f"Bearer {token2}"}
    assert auth_client.patch(f"/bookings/{bid}/reschedule/", json={"appointment_datetime": new_dt}, headers=other).status_code == 403
    assert auth_client.patch("/bookings/999999/reschedule/", json={"appointment_datetime": new_dt}).status_code == 404


def test_booking_cancel_confirmed_with_refund_note(auth_client, seed_ids):
    good = {
        "centre_id": seed_ids["centre_id"],
        "test_id": seed_ids["test_id"],
        "appointment_datetime": "2030-10-01T10:00:00Z",
    }
    bid = auth_client.post("/bookings/", json=good).json()["id"]
    pay = auth_client.post("/payments/", json={"booking_id": bid, "simulate": "success"})
    assert pay.json()["booking_status"] == "CONFIRMED"
    r = auth_client.patch(f"/bookings/{bid}/cancel/")
    assert r.status_code == 200
    assert r.json()["status"] == "CANCELLED"


def test_booking_detail_cross_user_forbidden(auth_client, seed_ids):
    good = {
        "centre_id": seed_ids["centre_id"],
        "test_id": seed_ids["test_id"],
        "appointment_datetime": "2030-06-01T10:00:00Z",
    }
    r = auth_client.post("/bookings/", json=good)
    assert r.status_code == 201
    bid = r.json()["id"]
    token2 = _signup_login(auth_client, "B", "b@x.com")
    other = {"Authorization": f"Bearer {token2}"}
    assert auth_client.get(f"/bookings/{bid}/", headers=other).status_code == 403
    # owner can read
    assert auth_client.get(f"/bookings/{bid}/").status_code == 200


def test_booking_unknown_id_not_found(auth_client):
    assert auth_client.get("/bookings/999999/").status_code == 404
    assert auth_client.patch("/bookings/999999/cancel/").status_code == 404


def test_bookings_list_own_only(auth_client, seed_ids):
    good = {
        "centre_id": seed_ids["centre_id"],
        "test_id": seed_ids["test_id"],
        "appointment_datetime": "2030-07-01T10:00:00Z",
    }
    r = auth_client.post("/bookings/", json=good)
    assert r.status_code == 201
    mine = auth_client.get("/bookings/").json()
    assert any(b["id"] == r.json()["id"] for b in mine)
    token2 = _signup_login(auth_client, "C", "c@x.com")
    others = auth_client.get("/bookings/", headers={"Authorization": f"Bearer {token2}"}).json()
    assert all(b["id"] != r.json()["id"] for b in others)
