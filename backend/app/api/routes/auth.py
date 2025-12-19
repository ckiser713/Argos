from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_db
from app.models import AuthUser
from app.services.auth_service import (
    TokenPair,
    authenticate_user,
    blacklist_access_token,
    create_user,
    ensure_initial_admin,
    get_current_user,
    issue_token_pair,
    oauth2_scheme,
    public_user,
    record_login,
    refresh_tokens,
    resolve_token,
    revoke_all_tokens,
    revoke_refresh_token,
    require_admin_user,
)

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: Optional[str] = None
    revoke_all: bool = False


class CreateUserRequest(BaseModel):
    username: str
    password: str
    roles: list[str] = Field(default_factory=lambda: ["user"])
    scopes: list[str] = Field(default_factory=list)
    is_active: bool = True


class BootstrapRequest(BaseModel):
    username: str
    password: str


def _client_ip(x_forwarded_for: Optional[str], client_host: Optional[str]) -> Optional[str]:
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return client_host


@router.post("/token", response_model=TokenPair)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_db),
    user_agent: Optional[str] = Header(default=None, convert_underscores=False),
    x_forwarded_for: Optional[str] = Header(default=None),
):
    """
    OAuth2-compatible login endpoint backed by the auth_users table.
    """
    user = await authenticate_user(session, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await record_login(session, user)
    token_pair = await issue_token_pair(
        session,
        user,
        user_agent=user_agent,
        ip_address=_client_ip(x_forwarded_for, None),
    )
    logger.info("User logged in", extra={"event": "auth.login.success", "username": user.username})
    return token_pair


@router.post("/token/refresh", response_model=TokenPair)
async def refresh_access_token(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_db),
    user_agent: Optional[str] = Header(default=None, convert_underscores=False),
    x_forwarded_for: Optional[str] = Header(default=None),
):
    return await refresh_tokens(
        session,
        body.refresh_token,
        user_agent=user_agent,
        ip_address=_client_ip(x_forwarded_for, None),
    )


@router.post("/logout")
async def logout(
    body: LogoutRequest,
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_db),
):
    payload, user = await resolve_token(token, session)
    await blacklist_access_token(session, payload, reason="logout")

    if body.revoke_all:
        await revoke_all_tokens(session, user)
    elif body.refresh_token:
        await revoke_refresh_token(session, body.refresh_token)

    logger.info("User logged out", extra={"event": "auth.logout", "username": user.username})
    return {"revoked": True}


@router.post("/users")
async def create_user_account(
    body: CreateUserRequest,
    session: AsyncSession = Depends(get_db),
    _admin_user: AuthUser = Depends(require_admin_user),
):
    try:
        user = await create_user(
            session,
            body.username,
            body.password,
            roles=body.roles,
            scopes=body.scopes,
            is_active=body.is_active,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return public_user(user)


@router.get("/me")
async def read_current_user(current_user: AuthUser = Depends(get_current_user)):
    return public_user(current_user)


@router.post("/bootstrap-admin")
async def bootstrap_admin(
    body: BootstrapRequest,
    session: AsyncSession = Depends(get_db),
):
    settings = get_settings()
    if settings.argos_env != "local":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Bootstrap is only allowed in local/dev.")
    try:
        user = await ensure_initial_admin(session, body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return public_user(user)
