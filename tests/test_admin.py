"""Task 1 TDD: admin role flag — guard, JWT claim, bootstrap.

The production /admin/bookings route lands in Task 2; these tests mount a
thin in-test probe route guarded by require_admin so the guard itself is
verified here. Verbatim cases from the brief are kept exact.
"""

import pytest
from fastapi.testclient import TestClient
from jose import jwt

from app.core.config import get_settings
from app.core.security import create_token, decode_token
from app.models.user import User


@pytest.fixture()
def user_client(client: TestClient) -> TestClient:
    client.post(
        "/auth/signup/",
        json={"name": "U", "email": "u@x.com", "password": "secret123"},
    )
    r = client.post("/auth/login/", data={"username": "u@x.com", "password": "secret123"})
    assert r.status_code == 200
    client.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return client


def test_non_admin_forbidden_on_admin_bookings(user_client):
    r = user_client.get("/admin/bookings")
    assert r.status_code == 403


def test_anonymous_unauthorized_on_admin_bookings(client):
    assert client.get("/admin/bookings").status_code == 401


def test_legacy_token_without_claim_decodes_and_is_non_admin(user_client):
    settings = get_settings()
    legacy = jwt.encode({"sub": "1"}, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    assert decode_token(legacy) == "1"  # decodes fine
    r = user_client.get(
        "/admin/bookings", headers={"Authorization": f"Bearer {legacy}"}
    )
    assert r.status_code in (401, 403)  # user id 1 exists but is non-admin -> 403


def test_legacy_token_forged_sub_is_non_admin(client: TestClient):
    settings = get_settings()
    legacy = jwt.encode({"sub": "9999"}, settings.JWT_SECRET, algorithm=settings.JWT_ALG)
    r = client.get("/admin/bookings", headers={"Authorization": f"Bearer {legacy}"})
    assert r.status_code == 401  # unknown user -> anonymous-equivalent 401


def test_create_token_carries_is_admin_claim_and_decode_keeps_sub():
    token = create_token("42", True)
    assert decode_token(token) == "42"
    payload = jwt.get_unverified_claims(token)
    assert payload["is_admin"] is True
    assert jwt.get_unverified_claims(create_token("42"))["is_admin"] is False


def test_old_create_token_call_still_valid():
    assert decode_token(create_token("7")) == "7"


def test_guard_reads_db_not_claim(client: TestClient):
    client.post(
        "/auth/signup/",
        json={"name": "Sneaky", "email": "sneaky@x.com", "password": "secret123"},
    )
    r = client.post("/auth/login/", data={"username": "sneaky@x.com", "password": "secret123"})
    user_id = jwt.get_unverified_claims(r.json()["access_token"])["sub"]
    forged = create_token(str(user_id), True)  # claim says admin, DB says not
    assert client.get(
        "/admin/bookings", headers={"Authorization": f"Bearer {forged}"}
    ).status_code == 403


def test_is_admin_defaults_false(client: TestClient):
    client.post(
        "/auth/signup/",
        json={"name": "N", "email": "n@x.com", "password": "secret123"},
    )
    r = client.post("/auth/login/", data={"username": "n@x.com", "password": "secret123"})
    assert jwt.get_unverified_claims(r.json()["access_token"])["is_admin"] is False


# --- Task 3 TDD: admin catalogue writes ---


@pytest.fixture()
def centre_id(admin_client: TestClient) -> int:
    return _seed_ids()["centre_id"]


@pytest.fixture()
def test_id(admin_client: TestClient) -> int:
    return _seed_ids()["test_id"]


def test_admin_offering_upsert_creates_then_updates(admin_client, centre_id, test_id):
    r1 = admin_client.put("/admin/offerings", json={"centre_id": centre_id, "test_id": test_id, "price": 100})
    assert r1.status_code == 200
    r2 = admin_client.put("/admin/offerings", json={"centre_id": centre_id, "test_id": test_id, "price": 150})
    assert r2.json()["price"] == 150


def test_admin_delete_referenced_centre_conflicts(admin_client, centre_id):
    r = admin_client.delete(f"/admin/centres/{centre_id}")
    assert r.status_code == 409


def test_admin_delete_referenced_test_conflicts(admin_client, test_id):
    r = admin_client.delete(f"/admin/tests/{test_id}")
    assert r.status_code == 409


def test_admin_offering_unknown_centre_404(admin_client, test_id):
    r = admin_client.put("/admin/offerings", json={"centre_id": 9999, "test_id": test_id, "price": 100})
    assert r.status_code == 404


def test_admin_offering_unknown_test_404(admin_client, centre_id):
    r = admin_client.put("/admin/offerings", json={"centre_id": centre_id, "test_id": 9999, "price": 100})
    assert r.status_code == 404


def test_admin_offering_zero_price_422(admin_client, centre_id, test_id):
    r = admin_client.put("/admin/offerings", json={"centre_id": centre_id, "test_id": test_id, "price": 0})
    assert r.status_code == 422


def test_admin_centre_crud(admin_client):
    r = admin_client.post("/admin/centres", json={"name": "New Lab", "location": "Delhi"})
    assert r.status_code == 201
    cid = r.json()["id"]
    r = admin_client.patch(f"/admin/centres/{cid}", json={"name": "Renamed Lab"})
    assert r.status_code == 200
    assert r.json()["name"] == "Renamed Lab"
    r = admin_client.delete(f"/admin/centres/{cid}")
    assert r.status_code in (200, 204)


def test_admin_test_crud(admin_client):
    r = admin_client.post("/admin/tests", json={"name": "Vitamin D"})
    assert r.status_code == 201
    tid = r.json()["id"]
    r = admin_client.patch(f"/admin/tests/{tid}", json={"name": "Vitamin D Plus"})
    assert r.status_code == 200
    assert r.json()["name"] == "Vitamin D Plus"
    r = admin_client.delete(f"/admin/tests/{tid}")
    assert r.status_code in (200, 204)


def test_admin_centre_unknown_404(admin_client):
    assert admin_client.patch("/admin/centres/9999", json={"name": "X"}).status_code == 404
    assert admin_client.delete("/admin/centres/9999").status_code == 404


def test_admin_test_unknown_404(admin_client):
    assert admin_client.patch("/admin/tests/9999", json={"name": "X"}).status_code == 404
    assert admin_client.delete("/admin/tests/9999").status_code == 404


def test_admin_writes_forbidden_for_non_admin(user_client, admin_client):
    ids = _seed_ids()
    # NOTE: user_client and admin_client share the underlying TestClient, so
    # headers hold the admin token; use an explicit non-admin token instead.
    token = _signup_login(admin_client, "Plain", "plain@x.com")
    hdr = {"Authorization": f"Bearer {token}"}
    assert admin_client.post("/admin/centres", json={"name": "X", "location": "Y"}, headers=hdr).status_code == 403
    assert admin_client.patch(f"/admin/centres/{ids['centre_id']}", json={"name": "X"}, headers=hdr).status_code == 403
    assert admin_client.delete(f"/admin/centres/{ids['centre_id']}", headers=hdr).status_code == 403
    assert admin_client.post("/admin/tests", json={"name": "X"}, headers=hdr).status_code == 403
    assert admin_client.patch(f"/admin/tests/{ids['test_id']}", json={"name": "X"}, headers=hdr).status_code == 403
    assert admin_client.delete(f"/admin/tests/{ids['test_id']}", headers=hdr).status_code == 403
    assert admin_client.put("/admin/offerings", json={**ids, "price": 100}, headers=hdr).status_code == 403


# --- Task 2 TDD: admin reads (bookings + payments) ---


def _signup_login(c: TestClient, name: str, email: str) -> str:
    assert c.post(
        "/auth/signup/", json={"name": name, "email": email, "password": "secret123"}
    ).status_code in (200, 201)
    r = c.post("/auth/login/", data={"username": email, "password": "secret123"})
    assert r.status_code == 200
    return r.json()["access_token"]


def _seed_ids() -> dict[str, int]:
    from app.models.offering import Offering
    from tests.conftest import _TestingSession

    db = _TestingSession()
    try:
        offering = db.query(Offering).order_by(Offering.id).first()
        assert offering is not None
        return {"centre_id": offering.centre_id, "test_id": offering.test_id}
    finally:
        db.close()


@pytest.fixture()
def admin_client(client: TestClient) -> TestClient:
    from app.seed import seed_db
    from tests.conftest import _TestingSession

    db = _TestingSession()
    try:
        seed_db(db)
    finally:
        db.close()
    _signup_login(client, "Boss", "boss@x.com")
    db = _TestingSession()
    try:
        user = db.query(User).filter(User.email == "boss@x.com").first()
        assert user is not None
        user.is_admin = True
        db.commit()
    finally:
        db.close()
    r = client.post("/auth/login/", data={"username": "boss@x.com", "password": "secret123"})
    assert r.status_code == 200
    client.headers.update({"Authorization": f"Bearer {r.json()['access_token']}"})
    return client


@pytest.fixture()
def other_booking(admin_client: TestClient) -> dict:
    ids = _seed_ids()
    token = _signup_login(admin_client, "Other", "other@x.com")
    hdr = {"Authorization": f"Bearer {token}"}
    r = admin_client.post(
        "/bookings/",
        json={**ids, "appointment_datetime": "2030-08-01T10:00:00Z"},
        headers=hdr,
    )
    assert r.status_code == 201
    booking = r.json()
    p = admin_client.post(
        "/payments/",
        json={"booking_id": booking["id"], "simulate": "success"},
        headers=hdr,
    )
    assert p.status_code == 200
    return {
        "booking_id": booking["id"],
        "user_email": "other@x.com",
        "provider_reference": p.json()["payment"]["provider_reference"],
        "token": token,
    }


def test_admin_sees_other_users_bookings(admin_client, other_booking):
    r = admin_client.get("/admin/bookings")
    assert r.status_code == 200
    assert any(b["user_email"] == other_booking["user_email"] for b in r.json())


def test_admin_bookings_status_filter(admin_client, other_booking):
    ids = _seed_ids()
    token = _signup_login(admin_client, "Pending", "pending@x.com")
    r = admin_client.post(
        "/bookings/",
        json={**ids, "appointment_datetime": "2030-09-01T10:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    r = admin_client.get("/admin/bookings", params={"status": "CONFIRMED"})
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected at least one CONFIRMED booking"
    assert all(b["status"] == "CONFIRMED" for b in rows)
    assert any(b["user_email"] == other_booking["user_email"] for b in rows)
    assert "centre_name" in rows[0] and "test_name" in rows[0]


def test_admin_payments_show_provider_reference(admin_client, other_booking):
    r = admin_client.get(
        "/admin/payments", params={"booking_id": other_booking["booking_id"]}
    )
    assert r.status_code == 200
    rows = r.json()
    assert rows, "expected at least one payment"
    assert any(
        p["provider_reference"] == other_booking["provider_reference"] for p in rows
    )
    assert all("booking_id" in p and "status" in p for p in rows)


# --- Final fix wave: scale gaps + input hardening ---


def test_admin_tests_lists_all_including_zero_offering(admin_client):
    r = admin_client.post("/admin/tests", json={"name": "Zero Offering Test"})
    assert r.status_code == 201
    tid = r.json()["id"]
    r = admin_client.get("/admin/tests")
    assert r.status_code == 200
    rows = r.json()
    assert any(t["id"] == tid and t["name"] == "Zero Offering Test" for t in rows)
    # also visible even though no offering exists for it
    assert all("id" in t and "name" in t for t in rows)


def test_admin_bookings_order_desc_and_stats(admin_client, other_booking):
    ids = _seed_ids()
    token = _signup_login(admin_client, "Second", "second@x.com")
    r = admin_client.post(
        "/bookings/",
        json={**ids, "appointment_datetime": "2030-10-01T10:00:00Z"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    second_id = r.json()["id"]
    r = admin_client.get("/admin/bookings", params={"order": "desc", "limit": 10})
    assert r.status_code == 200
    rows = r.json()
    assert rows and rows[0]["id"] == second_id
    assert [b["id"] for b in rows] == sorted(
        (b["id"] for b in rows), reverse=True
    )
    r = admin_client.get("/admin/bookings/stats")
    assert r.status_code == 200
    stats = r.json()
    assert stats["total"] >= 2
    assert stats["counts"].get("CONFIRMED", 0) >= 1
    assert stats["confirmed_sum"] > 0


def test_admin_payments_pagination(admin_client, other_booking):
    r = admin_client.get("/admin/payments", params={"limit": 1, "offset": 0})
    assert r.status_code == 200
    assert len(r.json()) == 1
    r = admin_client.get("/admin/payments", params={"limit": 300})
    assert r.status_code == 422  # over max 200
    r = admin_client.get("/admin/bookings", params={"limit": 300})
    assert r.status_code == 422


def test_admin_whitespace_names_rejected_422(admin_client):
    assert (
        admin_client.post(
            "/admin/centres", json={"name": "   ", "location": "Delhi"}
        ).status_code
        == 422
    )
    assert (
        admin_client.post(
            "/admin/centres", json={"name": "Lab", "location": "   "}
        ).status_code
        == 422
    )
    assert admin_client.post("/admin/tests", json={"name": "   "}).status_code == 422
    ids = _seed_ids()
    assert (
        admin_client.patch(
            f"/admin/centres/{ids['centre_id']}", json={"name": "   "}
        ).status_code
        == 422
    )
    assert (
        admin_client.patch(
            f"/admin/tests/{ids['test_id']}", json={"name": "   "}
        ).status_code
        == 422
    )


def test_admin_user_filter_escapes_like_wildcards(admin_client, other_booking):
    # literal %/_ must not widen into wildcards: no real email contains them,
    # so an unescaped filter would wrongly match everything.
    r = admin_client.get("/admin/bookings", params={"user": "%"})
    assert r.status_code == 200
    assert r.json() == []
    r = admin_client.get("/admin/bookings", params={"user": "_"})
    assert r.status_code == 200
    assert r.json() == []
