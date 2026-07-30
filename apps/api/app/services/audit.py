"""Append-only audit logging helper."""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.audit import AuditLog
from ..models.enums import AuditAction
from ..models.organisation import User


async def record(
    db: AsyncSession,
    *,
    actor: User | None,
    action: AuditAction,
    entity: str,
    entity_id: int | None = None,
    old_value: dict[str, Any] | None = None,
    new_value: dict[str, Any] | None = None,
    dealership_id: int | None = None,
    request_id: str | None = None,
) -> AuditLog:
    log = AuditLog(
        dealership_id=dealership_id or (actor.dealership_id if actor else 0),
        actor_id=actor.id if actor else None,
        actor_name=actor.full_name if actor else "system",
        action=action.value,
        entity=entity,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        request_id=request_id,
    )
    db.add(log)
    await db.flush()
    return log
