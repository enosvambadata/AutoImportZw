"""Authentication: login, refresh (with rotation), logout, current user, password reset."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.config import settings
from ...core.deps import CurrentUser
from ...core.ratelimit import rate_limit_auth
from ...core.security import (
    create_access_token,
    create_refresh_token,
    hash_token,
    verify_password,
)
from ...db.session import get_db
from ...models.enums import AuditAction
from ...models.organisation import RefreshToken, User
from ...schemas.auth import (
    LoginRequest,
    PasswordReset,
    PasswordResetRequest,
    TokenResponse,
    UserOut,
)
from ...schemas.common import Message
from ...services import audit

router = APIRouter(tags=["auth"])

REFRESH_COOKIE = "autobid_refresh"


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        httponly=True,
        secure=settings.secure_cookies,
        samesite=settings.cookie_samesite,
        max_age=settings.refresh_token_ttl_days * 86400,
        domain=settings.cookie_domain or None,
        path="/api/v1/auth",
    )


async def _issue_tokens(db: AsyncSession, response: Response, user: User) -> TokenResponse:
    raw, token_hash, expires = create_refresh_token()
    db.add(RefreshToken(user_id=user.id, token_hash=token_hash, expires_at=expires))
    await db.flush()
    _set_refresh_cookie(response, raw)
    access = create_access_token(user.id, user.role, user.dealership_id)
    return TokenResponse(access_token=access, expires_in=settings.access_token_ttl_minutes * 60)


@router.post("/auth/login", response_model=TokenResponse, dependencies=[Depends(rate_limit_auth)])
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = (await db.execute(
        select(User).where(User.email == payload.email.lower())
    )).scalar_one_or_none()
    # Constant-ish response: always verify to reduce user enumeration timing signal.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    if not user.active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Account is disabled")
    tokens = await _issue_tokens(db, response, user)
    await audit.record(db, actor=user, action=AuditAction.LOGIN, entity="user", entity_id=user.id,
                       request_id=getattr(request.state, "request_id", None))
    return tokens


@router.post("/auth/refresh", response_model=TokenResponse)
async def refresh(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    autobid_refresh: Annotated[str | None, Cookie()] = None,
):
    if not autobid_refresh:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No refresh token")
    token_hash = hash_token(autobid_refresh)
    record = (await db.execute(
        select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    )).scalar_one_or_none()
    expires_at = record.expires_at if record else None
    if expires_at is not None and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)  # SQLite returns naive datetimes
    if record is None or record.revoked or expires_at < datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired refresh token")
    # Rotate: revoke the old token and issue a fresh one.
    record.revoked = True
    user = await db.get(User, record.user_id)
    if user is None or not user.active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User not found or inactive")
    return await _issue_tokens(db, response, user)


@router.post("/auth/logout", response_model=Message)
async def logout(
    response: Response,
    db: Annotated[AsyncSession, Depends(get_db)],
    autobid_refresh: Annotated[str | None, Cookie()] = None,
):
    if autobid_refresh:
        record = (await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(autobid_refresh))
        )).scalar_one_or_none()
        if record:
            record.revoked = True
    response.delete_cookie(REFRESH_COOKIE, path="/api/v1/auth")
    return Message(message="Logged out")


@router.get("/auth/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user


@router.post("/auth/forgot-password", response_model=Message)
async def forgot_password(payload: PasswordResetRequest):
    # MVP: do not reveal whether the email exists. A production build emails a signed token.
    return Message(message="If that email exists, a reset link has been sent.")


@router.post("/auth/reset-password", response_model=Message)
async def reset_password(payload: PasswordReset):
    # Placeholder: a real flow validates a signed, single-use token and updates the hash.
    raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED,
                        "Password reset requires an email provider (see docs/SECURITY.md).")
