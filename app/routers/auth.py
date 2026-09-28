from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import create_token, hash_password, verify_password
from app.models.user import User
from app.schemas.auth import SignupIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _admin_emails() -> set[str]:
    raw = get_settings().ADMIN_EMAILS
    return {e.strip().lower() for e in raw.split(",") if e.strip()}


@router.post("/signup/", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: Session = Depends(get_db)) -> User:
    email = payload.email.strip().lower()
    if db.query(User).filter(User.email == email).first() is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")
    user = User(
        name=payload.name.strip(),
        email=email,
        password_hash=hash_password(payload.password),
        is_admin=email in _admin_emails(),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login/", response_model=TokenOut)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)) -> dict[str, str]:
    email = form.username.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(form.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )
    should_be_admin = email in _admin_emails()
    if user.is_admin != should_be_admin:
        user.is_admin = should_be_admin
        db.commit()
    return {"access_token": create_token(str(user.id), user.is_admin), "token_type": "bearer"}
