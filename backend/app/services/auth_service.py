from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from app.config import get_settings

SECRET_KEY = get_settings().auth_secret
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TokenData(BaseModel):
    username: str | None = None


class User(BaseModel):
    username: str
    disabled: bool = False


class UserInDB(User):
    hashed_password: str


# Default admin user - in production, load from database
# Password hash for 'admin' - change in production!
_DEFAULT_ADMIN_HASH = pwd_context.hash("admin")


def _get_users_db() -> dict[str, UserInDB]:
    """
    Get users database. In production, replace with actual database lookup.
    For development/strix, uses environment variable or defaults.
    """
    settings = get_settings()
    
    # Check for custom admin password from environment
    admin_password = os.environ.get("CORTEX_ADMIN_PASSWORD", "admin")
    admin_hash = pwd_context.hash(admin_password) if admin_password != "admin" else _DEFAULT_ADMIN_HASH
    
    return {
        "admin": UserInDB(
            username="admin",
            hashed_password=admin_hash,
            disabled=False,
        ),
        "cortex": UserInDB(
            username="cortex",
            hashed_password=pwd_context.hash(os.environ.get("CORTEX_USER_PASSWORD", "cortex")),
            disabled=False,
        ),
    }


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Generate password hash."""
    return pwd_context.hash(password)


def get_user(username: str) -> Optional[UserInDB]:
    """Get user from database."""
    users_db = _get_users_db()
    return users_db.get(username)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    """
    Authenticate user with username and password.
    Returns user if valid, None otherwise.
    """
    user = get_user(username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Create a JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str = Depends(oauth2_scheme)) -> TokenData:
    """Verify JWT token and return token data."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credentials_exception
    
    # Verify user still exists and is not disabled
    user = get_user(token_data.username)
    if user is None or user.disabled:
        raise credentials_exception
    
    return token_data
