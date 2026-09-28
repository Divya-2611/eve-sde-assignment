from datetime import UTC, datetime, timedelta

import bcrypt
from jose import JWTError, jwt

from app.core.config import get_settings


def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(p: str, h: str) -> bool:
    try:
        return bcrypt.checkpw(p.encode("utf-8"), h.encode("utf-8"))
    except ValueError:
        return False


def create_token(sub: str, is_admin: bool = False) -> str:
    settings = get_settings()
    exp = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)
    return jwt.encode(
        {"sub": sub, "is_admin": is_admin, "exp": exp},
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALG,
    )


def decode_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALG])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
    sub = payload.get("sub")
    if not sub:
        raise ValueError("invalid token")
    return str(sub)
