from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.booking import Booking
from app.models.user import User
from app.schemas.booking import BookingCreate, BookingOut, BookingReschedule
from app.services.booking_service import cancel_booking, create_booking, reschedule_booking

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("/", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    return create_booking(
        db,
        current_user,
        payload.centre_id,
        payload.test_id,
        payload.appointment_datetime,
    )


@router.get("/", response_model=list[BookingOut])
def list_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Booking]:
    return db.query(Booking).filter(Booking.user_id == current_user.id).order_by(Booking.id).all()


def _get_owned(db: Session, current_user: User, booking_id: int) -> Booking:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")
    return booking


@router.get("/{booking_id}/", response_model=BookingOut)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    return _get_owned(db, current_user, booking_id)


@router.patch("/{booking_id}/cancel/", response_model=BookingOut)
def cancel(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = _get_owned(db, current_user, booking_id)
    return cancel_booking(db, booking)


@router.patch("/{booking_id}/reschedule/", response_model=BookingOut)
def reschedule(
    booking_id: int,
    payload: BookingReschedule,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Booking:
    booking = _get_owned(db, current_user, booking_id)
    return reschedule_booking(db, booking, payload.appointment_datetime)
