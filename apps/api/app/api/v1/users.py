"""User management (admin only)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import require_admin
from ...core.security import hash_password
from ...db.session import get_db
from ...models.enums import AuditAction
from ...models.organisation import User
from ...schemas.auth import UserCreate, UserOut, UserUpdate
from ...services import audit

router = APIRouter(prefix="/users", tags=["users"])


@router.get("", response_model=list[UserOut])
async def list_users(
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    rows = (await db.execute(
        select(User).where(User.dealership_id == admin.dealership_id).order_by(User.id)
    )).scalars().all()
    return rows


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    existing = (await db.execute(
        select(User).where(User.email == payload.email.lower())
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with that email already exists")
    user = User(
        dealership_id=admin.dealership_id,
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email.lower(),
        password_hash=hash_password(payload.password),
        role=payload.role.value,
    )
    db.add(user)
    await db.flush()
    await audit.record(db, actor=admin, action=AuditAction.USER_CREATED, entity="user",
                       entity_id=user.id, new_value={"email": user.email, "role": user.role})
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    user = await db.get(User, user_id)
    if user is None or user.dealership_id != admin.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    old_role = user.role
    if payload.first_name is not None:
        user.first_name = payload.first_name
    if payload.last_name is not None:
        user.last_name = payload.last_name
    if payload.active is not None:
        user.active = payload.active
    if payload.password:
        user.password_hash = hash_password(payload.password)
    if payload.role is not None and payload.role.value != old_role:
        user.role = payload.role.value
        await audit.record(db, actor=admin, action=AuditAction.USER_ROLE_CHANGED, entity="user",
                           entity_id=user.id, old_value={"role": old_role},
                           new_value={"role": user.role})
    await db.flush()
    return user
