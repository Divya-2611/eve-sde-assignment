from fastapi import APIRouter, Depends, Query, Response, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_admin
from app.models.booking import Booking
from app.models.centre import Centre
from app.models.offering import Offering
from app.models.payment import Payment
from app.models.test import Test
from app.models.user import User
from app.schemas.admin import (
    AdminBookingOut,
    AdminBookingStatsOut,
    AdminCentreCreate,
    AdminCentreOut,
    AdminCentreUpdate,
    AdminOfferingOut,
    AdminOfferingUpsert,
    AdminPaymentOut,
    AdminTestCreate,
    AdminTestOut,
    AdminTestUpdate,
)
from app.services import admin_service

router = APIRouter(
    prefix="/admin",
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _apply_booking_filters(q, status: str | None, centre_id: int | None, user: str | None):
    if status is not None:
        q = q.filter(Booking.status == status)
    if centre_id is not None:
        q = q.filter(Booking.centre_id == centre_id)
    if user is not None:
        if user.isdigit():
            q = q.filter(Booking.user_id == int(user))
        else:
            q = q.filter(User.email.ilike(f"%{_escape_like(user)}%", escape="\\"))
    return q


@router.get("/bookings/stats", response_model=AdminBookingStatsOut)
def booking_stats(
    status: str | None = None,
    centre_id: int | None = None,
    user: str | None = None,
    db: Session = Depends(get_db),
) -> dict:
    base = _apply_booking_filters(
        db.query(Booking).join(User, User.id == Booking.user_id), status, centre_id, user
    )
    total = base.with_entities(func.count(Booking.id)).scalar() or 0
    counts: dict[str, int] = {}
    for st, n in (
        base.with_entities(Booking.status, func.count(Booking.id))
        .group_by(Booking.status)
        .all()
    ):
        counts[str(st)] = int(n)
    confirmed_sum = (
        base.with_entities(func.coalesce(func.sum(Booking.amount), 0))
        .filter(Booking.status == "CONFIRMED")
        .scalar()
        or 0
    )
    return {"total": total, "counts": counts, "confirmed_sum": float(confirmed_sum)}


@router.get("/bookings", response_model=list[AdminBookingOut])
def list_all_bookings(
    status: str | None = None,
    centre_id: int | None = None,
    user: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    order: str = Query(default="asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db),
) -> list[dict]:
    q = (
        db.query(Booking, User.email, Centre.name, Test.name)
        .join(User, User.id == Booking.user_id)
        .join(Centre, Centre.id == Booking.centre_id)
        .join(Test, Test.id == Booking.test_id)
    )
    q = _apply_booking_filters(q, status, centre_id, user)
    q = q.order_by(Booking.id.desc() if order == "desc" else Booking.id)
    rows = q.offset(offset).limit(limit).all()
    return [
        {
            "id": b.id,
            "user_id": b.user_id,
            "user_email": email,
            "centre_id": b.centre_id,
            "centre_name": centre_name,
            "test_id": b.test_id,
            "test_name": test_name,
            "appointment_datetime": b.appointment_datetime,
            "status": b.status,
            "amount": b.amount,
        }
        for b, email, centre_name, test_name in rows
    ]


@router.get("/payments", response_model=list[AdminPaymentOut])
def list_all_payments(
    booking_id: int | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> list[Payment]:
    q = db.query(Payment).order_by(Payment.id)
    if booking_id is not None:
        q = q.filter(Payment.booking_id == booking_id)
    return q.offset(offset).limit(limit).all()


@router.get("/tests", response_model=list[AdminTestOut])
def list_all_tests(db: Session = Depends(get_db)) -> list[Test]:
    return db.query(Test).order_by(Test.id).all()


@router.post("/centres", response_model=AdminCentreOut, status_code=status.HTTP_201_CREATED)
def create_centre(payload: AdminCentreCreate, db: Session = Depends(get_db)) -> Centre:
    return admin_service.create_centre(db, payload.name, payload.location)


@router.patch("/centres/{centre_id}", response_model=AdminCentreOut)
def update_centre(
    centre_id: int, payload: AdminCentreUpdate, db: Session = Depends(get_db)
) -> Centre:
    return admin_service.update_centre(db, centre_id, payload.name, payload.location)


@router.delete("/centres/{centre_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_centre(centre_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_centre(db, centre_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/tests", response_model=AdminTestOut, status_code=status.HTTP_201_CREATED)
def create_test(payload: AdminTestCreate, db: Session = Depends(get_db)) -> Test:
    return admin_service.create_test(db, payload.name)


@router.patch("/tests/{test_id}", response_model=AdminTestOut)
def update_test(test_id: int, payload: AdminTestUpdate, db: Session = Depends(get_db)) -> Test:
    return admin_service.update_test(db, test_id, payload.name)


@router.delete("/tests/{test_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_test(test_id: int, db: Session = Depends(get_db)) -> Response:
    admin_service.delete_test(db, test_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put("/offerings", response_model=AdminOfferingOut)
def upsert_offering(payload: AdminOfferingUpsert, db: Session = Depends(get_db)) -> Offering:
    return admin_service.upsert_offering(db, payload.centre_id, payload.test_id, payload.price)
