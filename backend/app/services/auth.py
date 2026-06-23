import base64
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.user import User
from app.services.progress import DEFAULT_USERNAME

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
TOKEN_TTL = timedelta(days=30)


def normalize_username(username: str) -> str:
    return username.strip().lower()


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_user(
    db: Session,
    *,
    username: str,
    password: str,
    display_name: str | None = None,
) -> User:
    normalized_username = normalize_username(username)
    existing = db.scalar(select(User).where(User.username == normalized_username))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists")

    first_registered_user = (
        db.scalar(select(User.id).where(User.username != DEFAULT_USERNAME).limit(1)) is None
    )
    user = User(
        username=normalized_username,
        display_name=display_name.strip() if display_name and display_name.strip() else username,
        password_hash=hash_password(password),
        is_admin=first_registered_user,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == normalize_username(username)))
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    return user


def create_access_token(user: User) -> str:
    expires_at = int((datetime.now(UTC) + TOKEN_TTL).timestamp())
    payload = {"sub": str(user.id), "exp": expires_at}
    payload_bytes = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    signature = hmac.new(
        settings.secret_key.encode(),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    return f"{_b64encode(payload_bytes)}.{_b64encode(signature)}"


def user_id_from_token(token: str) -> UUID:
    try:
        payload_part, signature_part = token.split(".", maxsplit=1)
        payload_bytes = _b64decode(payload_part)
        signature = _b64decode(signature_part)
    except ValueError as exc:
        raise _invalid_token() from exc

    expected_signature = hmac.new(
        settings.secret_key.encode(),
        payload_bytes,
        hashlib.sha256,
    ).digest()
    if not hmac.compare_digest(signature, expected_signature):
        raise _invalid_token()

    try:
        payload = json.loads(payload_bytes)
        expires_at = int(payload["exp"])
        user_id = UUID(payload["sub"])
    except (KeyError, TypeError, ValueError) as exc:
        raise _invalid_token() from exc

    if expires_at < int(datetime.now(UTC).timestamp()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")

    return user_id


def _invalid_token() -> HTTPException:
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _b64decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)
