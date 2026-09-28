import os

from sqlalchemy.orm import Session

from app.core.database import Base, SessionLocal, engine
from app.core.security import hash_password
from app.models.centre import Centre
from app.models.offering import Offering
from app.models.test import Test
from app.models.user import User

_SEED = [
    ("City Lab - Andheri", "Mumbai", [("CBC", 299.0), ("Lipid Profile", 799.0), ("Thyroid Panel", 549.0)]),
    ("City Lab - Koramangala", "Bengaluru", [("CBC", 349.0), ("HbA1c", 499.0)]),
]


def seed_db(session: Session) -> None:
    if session.query(Centre).first() is not None:
        return
    for centre_name, location, tests in _SEED:
        centre = Centre(name=centre_name, location=location)
        session.add(centre)
        session.flush()
        for test_name, price in tests:
            test = session.query(Test).filter(Test.name == test_name).first()
            if test is None:
                test = Test(name=test_name)
                session.add(test)
                session.flush()
            session.add(Offering(centre_id=centre.id, test_id=test.id, price=price))
    session.commit()


def ensure_admin(session: Session) -> None:
    """Create the bootstrap admin from ADMIN_EMAIL/ADMIN_PASSWORD if set.
    Idempotent: skips when the user already exists."""
    email = os.environ.get("ADMIN_EMAIL", "").strip().lower()
    password = os.environ.get("ADMIN_PASSWORD", "")
    if not email or not password:
        return
    if session.query(User).filter(User.email == email).first() is not None:
        return
    session.add(
        User(
            name="Admin",
            email=email,
            password_hash=hash_password(password),
            is_admin=True,
        )
    )
    session.commit()


def main() -> None:
    # create_all is a no-op on a migrated DB; it lets `make seed` work on a
    # fresh database without a separate migrate step.
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        seed_db(db)
        ensure_admin(db)
    finally:
        db.close()
    print("seed: ok")


if __name__ == "__main__":
    main()
