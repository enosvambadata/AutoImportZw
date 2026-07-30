"""Dealership settings (read for all; write for admins)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import CurrentUser, require_admin
from ...db.session import get_db
from ...models.enums import AuditAction
from ...models.organisation import Dealership, User
from ...schemas.org import DealershipOut, DealershipUpdate
from ...services import audit

router = APIRouter(prefix="/dealership", tags=["dealership"])


@router.get("", response_model=DealershipOut)
async def get_dealership(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    dealership = await db.get(Dealership, user.dealership_id)
    if dealership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dealership not found")
    return dealership


@router.patch("", response_model=DealershipOut)
async def update_dealership(
    payload: DealershipUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    dealership = await db.get(Dealership, admin.dealership_id)
    if dealership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Dealership not found")
    changes = payload.model_dump(exclude_unset=True)
    old = {k: getattr(dealership, k) for k in changes}
    for key, value in changes.items():
        setattr(dealership, key, value)
    await db.flush()
    await audit.record(db, actor=admin, action=AuditAction.SETTINGS_CHANGED, entity="dealership",
                       entity_id=dealership.id, old_value={k: str(v) for k, v in old.items()},
                       new_value={k: str(v) for k, v in changes.items()})
    return dealership
