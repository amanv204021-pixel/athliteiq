"""
Password hashing + JWT issuing/verification.

BUGFIX (critical): the original used passlib's CryptContext with bcrypt.
Against bcrypt >= 4.1 that combination raises
    ValueError: password cannot be longer than 72 bytes
on *every* signup, because passlib's backend-detection probe feeds an
over-long test password to bcrypt. passlib is unmaintained (last release
2020) and broken on modern bcrypt, so we now call bcrypt directly and
truncate to its documented 72-byte limit ourselves.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import models
from .config import settings
from .database import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")

# bcrypt hard-limits input to 72 bytes and errors on anything longer.
BCRYPT_MAX_BYTES = 72


def _prepare(password: str) -> bytes:
    """Encode and safely truncate to bcrypt's 72-byte limit."""
    return password.encode("utf-8")[:BCRYPT_MAX_BYTES]


def hash_password(password: str) -> str:
    return bcrypt.hashpw(_prepare(password), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(_prepare(plain), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        # Malformed/legacy hash in the DB -> treat as a failed login.
        return False


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    # BUGFIX: datetime.utcnow() is deprecated in Python 3.12+ and returns a
    # naive datetime. Use an explicit UTC-aware one.
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)
) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except (JWTError, ValueError):
        raise credentials_exception

    # BUGFIX: int(user_id) could raise ValueError on a tampered token and
    # surface as an unhandled 500. Now guarded.
    try:
        uid = int(user_id)
    except (TypeError, ValueError):
        raise credentials_exception

    user = db.query(models.User).filter(models.User.id == uid).first()
    if user is None:
        raise credentials_exception
    return user


def require_scout(current_user: models.User = Depends(get_current_user)) -> models.User:
    """Dependency for endpoints only scouts/admins may call."""
    if current_user.role not in ("scout", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is restricted to scouts and admins",
        )
    return current_user
