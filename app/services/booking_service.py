from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.offering import Offering
from app.models.user import User

CANCELLABLE = {"PENDING", "FAILED", "CONFIRMED"}
RESCHEDULABLE = {"PENDING", "FAILED", "CONFIRMED"}


def create_booking(
    db: Session,
    user: User,
    centre_id: int,
    test_id: int,
    appointment_datetime: datetime,
) -> Booking:
    offering = (
        db.query(Offering)
        .filter(Offering.centre_id == centre_id, Offering.test_id == test_id)
        .first()
    )
    if offering is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Offering not found")
    appt = appointment_datetime
    if appt.tzinfo is None:
        appt = appt.replace(tzinfo=UTC)
    if appt <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment must be in the future",
        )
    booking = Booking(
        user_id=user.id,
        centre_id=centre_id,
        test_id=test_id,
        appointment_datetime=appt,
        status="PENDING",
        amount=offering.price,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)
    return booking


def cancel_booking(db: Session, booking: Booking) -> Booking:
    if booking.status not in CANCELLABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only PENDING, FAILED or CONFIRMED bookings can be cancelled",
        )
    booking.status = "CANCELLED"
    db.commit()
    db.refresh(booking)
    return booking


def reschedule_booking(
    db: Session, booking: Booking, appointment_datetime: datetime
) -> Booking:
    if booking.status not in RESCHEDULABLE:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Only PENDING, FAILED or CONFIRMED bookings can be rescheduled",
        )
    appt = appointment_datetime
    if appt.tzinfo is None:
        appt = appt.replace(tzinfo=UTC)
    if appt <= datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Appointment must be in the future",
        )
    booking.appointment_datetime = appt
    db.commit()
    db.refresh(booking)
    return booking
