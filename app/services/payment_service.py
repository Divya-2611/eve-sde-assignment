import random
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.payment import Payment
from app.models.user import User
from app.models.webhook_event import WebhookEvent

# Mock provider outcome weight: 70% SUCCESS, 30% FAILED.
MOCK_SUCCESS_RATE = 0.7
# Simulated provider processing time (seconds). Patched to 0 in tests.
MOCK_PROCESSING_SECONDS = 2.0


def create_payment(
    db: Session, user: User, booking_id: int, simulate: str
) -> tuple[Payment, Booking]:
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")
    if booking.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot pay for a cancelled booking"
        )
    if booking.status == "CONFIRMED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")
    existing = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.status == "SUCCESS")
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")
    sim = simulate.lower()
    if sim not in ("success", "fail"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid simulate value"
        )
    payment_status = "SUCCESS" if sim == "success" else "FAILED"
    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status=payment_status,
        provider_reference=uuid4().hex,
    )
    db.add(payment)
    booking.status = "CONFIRMED" if payment_status == "SUCCESS" else "FAILED"
    try:
        db.commit()
    except IntegrityError:
        # Concurrent duplicate delivery: another worker won the race.
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid"
        )
    db.refresh(payment)
    db.refresh(booking)
    return payment, booking


def process_webhook(
    db: Session,
    event_id: str,
    provider_reference: str,
    webhook_status: str,
    booking_id: int | None = None,
    raw_payload: dict | None = None,
) -> Payment:
    norm = webhook_status.upper()
    if norm not in ("SUCCESS", "FAILED"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid status")

    # 1. event_id short-circuit: already processed -> return existing payment, no dup.
    seen = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
    if seen is not None:
        payment = (
            db.query(Payment).filter(Payment.provider_reference == seen.provider_reference).first()
        )
        if payment is None:
            payment = (
                db.query(Payment).filter(Payment.provider_reference == provider_reference).first()
            )
        if payment is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
        return payment

    # 2. lookup-or-create payment by provider_reference.
    payment = db.query(Payment).filter(Payment.provider_reference == provider_reference).first()
    if payment is None:
        if booking_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="booking_id is required"
            )
        booking = db.get(Booking, booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
        payment = Payment(
            booking_id=booking.id,
            amount=booking.amount,
            status=norm,
            provider_reference=provider_reference,
        )
        db.add(payment)
        try:
            db.flush()
        except IntegrityError:
            # Lost a concurrent race on provider_reference: another worker
            # inserted the payment first. Reconcile to the winner.
            db.rollback()
            payment = (
                db.query(Payment)
                .filter(Payment.provider_reference == provider_reference)
                .first()
            )
            if payment is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Duplicate webhook delivery",
                )
            booking = db.get(Booking, payment.booking_id)
            if booking is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found"
                )
    else:
        booking = db.get(Booking, payment.booking_id)
        if booking is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    # 3. forward-only transition: never CONFIRMED -> other; CANCELLED ack, no transition.
    if booking.status in ("CONFIRMED", "CANCELLED"):
        pass
    else:
        if norm == "SUCCESS":
            booking.status = "CONFIRMED"
            payment.status = "SUCCESS"
        else:
            booking.status = "FAILED"
            payment.status = "FAILED"

    # 4. insert event in the same transaction.
    db.add(
        WebhookEvent(
            event_id=event_id,
            provider_reference=payment.provider_reference,
            payload=raw_payload or {},
            processed_at=datetime.now(UTC),
        )
    )
    try:
        db.commit()
    except IntegrityError:
        # Lost a concurrent race on event_id (or provider_reference):
        # another worker committed first. Roll back and return the
        # winner's payment so the caller still acks 200.
        db.rollback()
        seen = db.query(WebhookEvent).filter(WebhookEvent.event_id == event_id).first()
        if seen is not None:
            payment = (
                db.query(Payment)
                .filter(Payment.provider_reference == seen.provider_reference)
                .first()
            )
            if payment is not None:
                return payment
        payment = (
            db.query(Payment).filter(Payment.provider_reference == provider_reference).first()
        )
        if payment is None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Duplicate webhook delivery"
            )
        return payment
    db.refresh(payment)
    return payment


def mock_charge_booking(
    db: Session, user: User, booking_id: int
) -> tuple[str, str, Payment, Booking]:
    """Simulate an external provider: create a PENDING payment, wait like a
    real provider would, then resolve 70/30 through the forward-only
    transition. The PENDING stage is real in the DB, not just UI text."""
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if booking is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    if booking.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not your booking")
    if booking.status == "CANCELLED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot pay for a cancelled booking"
        )
    if booking.status == "CONFIRMED":
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")
    existing = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.status == "SUCCESS")
        .first()
    )
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")
    event_id = f"mock-{uuid4().hex}"
    provider_reference = f"mock-{uuid4().hex}"
    payment = Payment(
        booking_id=booking.id,
        amount=booking.amount,
        status="PENDING",
        provider_reference=provider_reference,
    )
    db.add(payment)
    db.add(
        WebhookEvent(
            event_id=event_id,
            provider_reference=provider_reference,
            payload={"provider": "mock", "event_id": event_id},
            processed_at=datetime.now(UTC),
        )
    )
    db.commit()
    db.refresh(payment)
    # Provider processing window: payment is visibly PENDING in the DB.
    time.sleep(MOCK_PROCESSING_SECONDS)
    # Re-check after the window: a concurrent charge may have succeeded first.
    # The loser drops its PENDING row (no money moved) instead of double-charging.
    winner = (
        db.query(Payment)
        .filter(Payment.booking_id == booking.id, Payment.status == "SUCCESS")
        .first()
    )
    if winner is not None:
        db.delete(payment)
        db.commit()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid")
    outcome = "SUCCESS" if random.random() < MOCK_SUCCESS_RATE else "FAILED"
    if outcome == "SUCCESS":
        payment.status = "SUCCESS"
        booking.status = "CONFIRMED"
    else:
        payment.status = "FAILED"
        booking.status = "FAILED"
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Booking is already paid"
        )
    db.refresh(payment)
    db.refresh(booking)
    return outcome, event_id, payment, booking
