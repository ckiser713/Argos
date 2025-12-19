from __future__ import annotations

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Iterable, Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import AuthRefreshToken, AuthTokenBlacklist, AuthUser

logger = logging.getLogger(__name__)

ALGORITHM = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenPair(BaseModel):
    access_token: str
    access_token_expires_at: datetime
    refresh_token: Optional[str] = None
    refresh_token_expires_at: Optional[datetime] = None
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str
    username: str
    roles: list[str] = []
    scopes: list[str] = []
    token_version: int
    jti: str
    token_type: str
    exp: datetime


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def _normalize(values: Optional[Iterable[str]]) -> list[str]:
    if not values:
        return []
    return sorted({v.strip() for v in values if v and v.strip()})


def _serialize(values: list[str]) -> str:
    return ",".join(values) if values else ""


def _deserialize(value: Optional[str]) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def public_user(user: AuthUser) -> dict:
    """Return a serializable view of the user without secrets."""
    return {
        "id": user.id,
        "username": user.username,
        "roles": _deserialize(user.roles),
        "scopes": _deserialize(user.scopes),
        "is_active": bool(user.is_active),
        "last_login_at": user.last_login_at,
    }


async def _get_user_by_username(session: AsyncSession, username: str) -> Optional[AuthUser]:
    result = await session.execute(
        select(AuthUser).where(AuthUser.username == username)
    )
    return result.scalar_one_or_none()


async def users_exist(session: AsyncSession) -> bool:
    result = await session.execute(select(AuthUser.id).limit(1))
    return result.first() is not None


async def create_user(
    session: AsyncSession,
    username: str,
    password: str,
    *,
    roles: Optional[Iterable[str]] = None,
    scopes: Optional[Iterable[str]] = None,
    is_active: bool = True,
) -> AuthUser:
    existing = await _get_user_by_username(session, username)
    if existing:
        raise ValueError("Username already exists")

    normalized_roles = _normalize(roles) or ["user"]
    normalized_scopes = _normalize(scopes)

    user = AuthUser(
        username=username,
        password_hash=get_password_hash(password),
        roles=_serialize(normalized_roles),
        scopes=_serialize(normalized_scopes),
        is_active=is_active,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    logger.info("Created user", extra={"event": "auth.user.created", "username": username})
    return user


async def ensure_initial_admin(
    session: AsyncSession,
    username: str,
    password: str,
) -> AuthUser:
    """Create the first admin user if none exist."""
    if await users_exist(session):
        raise ValueError("Users already exist; bootstrap admin is not allowed.")
    return await create_user(session, username, password, roles=["admin"], scopes=[], is_active=True)


async def authenticate_user(session: AsyncSession, username: str, password: str) -> Optional[AuthUser]:
    user = await _get_user_by_username(session, username)
    if not user or not user.is_active:
        return None
    if not verify_password(password, user.password_hash):
        return None
    return user


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _build_access_token(user: AuthUser, *, expires_at: datetime, jti: str) -> str:
    settings = get_settings()
    payload = {
        "sub": user.id,
        "username": user.username,
        "roles": _deserialize(user.roles),
        "scopes": _deserialize(user.scopes),
        "tv": user.token_version,
        "jti": jti,
        "type": "access",
        "exp": expires_at,
        "iat": _now(),
    }
    return jwt.encode(payload, settings.auth_secret, algorithm=ALGORITHM)


async def _store_refresh_token(
    session: AsyncSession,
    user: AuthUser,
    raw_token: str,
    expires_at: datetime,
    user_agent: Optional[str],
    ip_address: Optional[str],
) -> AuthRefreshToken:
    token_record = AuthRefreshToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=expires_at,
        user_agent=user_agent,
        ip_address=ip_address,
    )
    session.add(token_record)
    await session.commit()
    await session.refresh(token_record)
    return token_record


async def issue_token_pair(
    session: AsyncSession,
    user: AuthUser,
    *,
    include_refresh: bool = True,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> TokenPair:
    settings = get_settings()
    access_expiry_minutes = max(settings.access_token_minutes, 1)
    refresh_expiry_days = max(settings.refresh_token_days, 1)

    access_expires_at = _now() + timedelta(minutes=access_expiry_minutes)
    access_token = _build_access_token(user, expires_at=access_expires_at, jti=uuid.uuid4().hex)

    refresh_token: Optional[str] = None
    refresh_expires_at: Optional[datetime] = None
    if include_refresh:
        refresh_expires_at = _now() + timedelta(days=refresh_expiry_days)
        refresh_token = secrets.token_urlsafe(48)
        await _store_refresh_token(
            session,
            user,
            refresh_token,
            refresh_expires_at,
            user_agent=user_agent,
            ip_address=ip_address,
        )

    return TokenPair(
        access_token=access_token,
        access_token_expires_at=access_expires_at,
        refresh_token=refresh_token,
        refresh_token_expires_at=refresh_expires_at,
    )


async def _is_blacklisted(session: AsyncSession, jti: str) -> bool:
    result = await session.execute(
        select(AuthTokenBlacklist).where(AuthTokenBlacklist.jti == jti)
    )
    record = result.scalar_one_or_none()
    if not record:
        return False
    if record.expires_at and record.expires_at < _now():
        # Cleanup expired blacklist entries lazily
        await session.delete(record)
        await session.commit()
        return False
    return True


async def resolve_token(
    token: str,
    session: AsyncSession,
) -> Tuple[TokenPayload, AuthUser]:
    try:
        payload = jwt.decode(token, get_settings().auth_secret, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise _credentials_exception() from exc

    token_type = payload.get("type")
    token_version = payload.get("tv") or payload.get("token_version")
    jti = payload.get("jti")
    sub = payload.get("sub")
    username = payload.get("username")
    exp_raw = payload.get("exp")

    if token_type != "access" or not sub or not jti or token_version is None:
        raise _credentials_exception()

    exp_dt = (
        datetime.fromtimestamp(exp_raw, tz=timezone.utc)
        if isinstance(exp_raw, (int, float))
        else _now()
    )

    token_payload = TokenPayload(
        sub=str(sub),
        username=str(username) if username else "",
        roles=list(payload.get("roles") or []),
        scopes=list(payload.get("scopes") or []),
        token_version=int(token_version),
        jti=str(jti),
        token_type=str(token_type),
        exp=exp_dt,
    )

    if await _is_blacklisted(session, token_payload.jti):
        raise _credentials_exception()

    user = await session.get(AuthUser, token_payload.sub)
    if not user or not user.is_active or user.token_version != token_payload.token_version:
        raise _credentials_exception()

    return token_payload, user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
) -> AuthUser:
    _, user = await resolve_token(token, session)
    return user


async def require_admin_user(user: AuthUser = Depends(get_current_user)) -> AuthUser:
    if "admin" not in _deserialize(user.roles):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin role required",
        )
    return user


async def blacklist_access_token(
    session: AsyncSession,
    payload: TokenPayload,
    reason: Optional[str] = None,
) -> None:
    record = AuthTokenBlacklist(
        jti=payload.jti,
        user_id=payload.sub,
        token_type=payload.token_type,
        reason=reason,
        expires_at=payload.exp,
    )
    session.add(record)
    await session.commit()


async def revoke_refresh_token(
    session: AsyncSession,
    raw_refresh_token: str,
) -> bool:
    token_hash = _hash_token(raw_refresh_token)
    result = await session.execute(
        select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()
    if not token_record:
        return False
    token_record.revoked_at = _now()
    await session.commit()
    return True


async def revoke_all_tokens(session: AsyncSession, user: AuthUser) -> None:
    now = _now()
    user.token_version += 1
    result = await session.execute(
        select(AuthRefreshToken).where(
            AuthRefreshToken.user_id == user.id,
            AuthRefreshToken.revoked_at.is_(None),
        )
    )
    for token_record in result.scalars().all():
        token_record.revoked_at = now
    await session.commit()


async def refresh_tokens(
    session: AsyncSession,
    refresh_token: str,
    *,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> TokenPair:
    token_hash = _hash_token(refresh_token)
    result = await session.execute(
        select(AuthRefreshToken).where(AuthRefreshToken.token_hash == token_hash)
    )
    token_record = result.scalar_one_or_none()
    if not token_record or token_record.revoked_at or token_record.expires_at <= _now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    user = await session.get(AuthUser, token_record.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    token_record.last_used_at = _now()
    await session.commit()

    return await issue_token_pair(
        session,
        user,
        include_refresh=False,
        user_agent=user_agent,
        ip_address=ip_address,
    )


async def record_login(session: AsyncSession, user: AuthUser) -> None:
    user.last_login_at = _now()
    await session.commit()
