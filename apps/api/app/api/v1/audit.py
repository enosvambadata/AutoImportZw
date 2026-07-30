"""Audit log (read-only, dealership-scoped)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import CurrentUser
from ...db.session import get_db
from ...models.audit import AuditLog
from ...schemas.common import Page

router = APIRouter(prefix="/audit-logs", tags=["audit"])


class AuditLogOut(BaseModel):
    model_config = {"from_attributes": True}
    id: int
    actor_name: str | None
    action: str
    entity: str
    entity_id: int | None
    old_value: dict | None
    new_value: dict | None
    created_at: datetime


@router.get("", response_model=Page[AuditLogOut])
async def list_audit(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    entity: str | None = None,
    entity_id: int | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
):
    stmt = select(AuditLog).where(AuditLog.dealership_id == user.dealership_id)
    if entity:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(
        stmt.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return Page(items=rows, total=total, page=page, page_size=page_size)
