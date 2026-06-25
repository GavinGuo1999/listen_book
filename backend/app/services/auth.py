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

pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")
TOKEN_TTL = timedelta(days=30)
USERNAME_MIN_LENGTH = 3
USERNAME_MAX_LENGTH = 64
PASSWORD_MIN_LENGTH = 6
PASSWORD_MAX_LENGTH = 128


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
) -> User:
    normalized_username = normalize_username(username)
    validate_username(normalized_username)
    validate_password(password)

    existing = db.scalar(select(User).where(User.username == normalized_username))
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="用户名已存在")

    user = User(
        username=normalized_username,
        display_name=normalized_username,
        password_hash=hash_password(password),
        is_admin=False,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def bootstrap_admin_user(db: Session, *, username: str, password: str) -> User:
    normalized_username = normalize_username(username)
    validate_username(normalized_username)
    validate_password(password)

    user = db.scalar(select(User).where(User.username == normalized_username))
    if user is None:
        user = User(
            username=normalized_username,
            display_name=normalized_username,
            password_hash=hash_password(password),
            is_admin=True,
            is_active=True,
        )
        db.add(user)
    else:
        user.display_name = user.display_name or normalized_username
        user.password_hash = hash_password(password)
        user.is_admin = True
        user.is_active = True
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, *, username: str, password: str) -> User:
    normalized_username = normalize_username(username)
    if not normalized_username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入用户名")
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入密码")

    user = db.scalar(select(User).where(User.username == normalized_username))
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名不存在")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="用户已停用")
    if not verify_password(password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="密码不正确")
    return user


def validate_username(username: str) -> None:
    if not username:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入用户名")
    if len(username) < USERNAME_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户名至少需要 {USERNAME_MIN_LENGTH} 个字符",
        )
    if len(username) > USERNAME_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"用户名不能超过 {USERNAME_MAX_LENGTH} 个字符",
        )


def validate_password(password: str) -> None:
    if not password:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请输入密码")
    if len(password) < PASSWORD_MIN_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码至少需要 {PASSWORD_MIN_LENGTH} 个字符",
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"密码不能超过 {PASSWORD_MAX_LENGTH} 个字符",
        )


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
