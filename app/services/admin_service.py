from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.booking import Booking
from app.models.centre import Centre
from app.models.offering import Offering
from app.models.test import Test


def create_centre(db: Session, name: str, location: str) -> Centre:
    centre = Centre(name=name.strip(), location=location.strip())
    db.add(centre)
    db.commit()
    db.refresh(centre)
    return centre


def update_centre(
    db: Session, centre_id: int, name: str | None = None, location: str | None = None
) -> Centre:
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    if name is not None:
        centre.name = name.strip()
    if location is not None:
        centre.location = location.strip()
    db.commit()
    db.refresh(centre)
    return centre


def delete_centre(db: Session, centre_id: int) -> None:
    centre = db.query(Centre).filter(Centre.id == centre_id).first()
    if centre is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    if db.query(Offering).filter(Offering.centre_id == centre_id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Centre is referenced by offerings"
        )
    if db.query(Booking).filter(Booking.centre_id == centre_id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Centre is referenced by bookings"
        )
    db.delete(centre)
    db.commit()


def create_test(db: Session, name: str) -> Test:
    name = name.strip()
    if db.query(Test).filter(Test.name == name).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Test with this name already exists"
        )
    test = Test(name=name)
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


def update_test(db: Session, test_id: int, name: str | None = None) -> Test:
    test = db.query(Test).filter(Test.id == test_id).first()
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    if name is not None:
        name = name.strip()
        existing = db.query(Test).filter(Test.name == name, Test.id != test_id).first()
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Test with this name already exists"
            )
        test.name = name
    db.commit()
    db.refresh(test)
    return test


def delete_test(db: Session, test_id: int) -> None:
    test = db.query(Test).filter(Test.id == test_id).first()
    if test is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    if db.query(Offering).filter(Offering.test_id == test_id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Test is referenced by offerings"
        )
    if db.query(Booking).filter(Booking.test_id == test_id).first() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Test is referenced by bookings"
        )
    db.delete(test)
    db.commit()


def upsert_offering(db: Session, centre_id: int, test_id: int, price: float) -> Offering:
    if db.query(Centre).filter(Centre.id == centre_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Centre not found")
    if db.query(Test).filter(Test.id == test_id).first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    offering = (
        db.query(Offering)
        .filter(Offering.centre_id == centre_id, Offering.test_id == test_id)
        .first()
    )
    if offering is None:
        offering = Offering(centre_id=centre_id, test_id=test_id, price=price)
        db.add(offering)
    else:
        offering.price = price
    db.commit()
    db.refresh(offering)
    return offering
