from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models.booking import Booking
from app.models.user import User
from app.schemas.payment import MockChargeIn, MockChargeOut, PaymentCreate, PaymentResult, WebhookIn
from app.services.payment_service import create_payment, mock_charge_booking, process_webhook

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("/", response_model=PaymentResult, status_code=status.HTTP_200_OK)
def create(
    payload: PaymentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    payment, booking = create_payment(db, current_user, payload.booking_id, payload.simulate)
    return {"payment": payment, "booking_status": booking.status}


@router.post("/webhook/", status_code=status.HTTP_200_OK)
def webhook(payload: WebhookIn, db: Session = Depends(get_db)) -> dict:
    payment = process_webhook(
        db,
        event_id=payload.event_id,
        provider_reference=payload.provider_reference,
        webhook_status=payload.status,
        booking_id=payload.booking_id,
        raw_payload=payload.model_dump(),
    )
    booking = db.get(Booking, payment.booking_id)
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return {
        "ok": True,
        "event_id": payload.event_id,
        "payment_id": payment.id,
        "booking_status": booking.status,
    }


@router.post("/mock/charge", response_model=MockChargeOut, status_code=status.HTTP_200_OK)
def mock_charge(
    payload: MockChargeIn,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict:
    outcome, event_id, payment, booking = mock_charge_booking(db, current_user, payload.booking_id)
    return {
        "outcome": outcome,
        "event_id": event_id,
        "provider_reference": payment.provider_reference,
        "payment_id": payment.id,
        "booking_status": booking.status,
    }
