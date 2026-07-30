"""Data-connector status and catalogue sync (Copart, SYNETIQ, Auto Trader, demo)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import CurrentUser, require_admin
from ...db.session import get_db
from ...integrations.connectors import connector_status, get_catalogue_connector
from ...models.enums import AuditAction
from ...models.organisation import User
from ...services import audit
from ...services.ingestion import ingest

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("")
async def list_connectors(user: CurrentUser):
    """Report each provider connector and whether its credentials are configured."""
    return {
        "connectors": connector_status(),
        "note": ("Real providers require an official API account/agreement and credentials. "
                 "The demo connector is always available so the ingestion pipeline can run."),
    }


@router.post("/{name}/sync")
async def sync_connector(
    name: str,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = 200,
):
    """Pull the connector's catalogue and upsert it into this dealership's listings (admin)."""
    connector = get_catalogue_connector(name)
    if connector is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Unknown catalogue connector: {name}")
    if not connector.is_configured():
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"The '{name}' connector is not configured. Set its API credentials (see "
            "docs/API_INTEGRATIONS.md) to enable it.")
    try:
        listings = connector.fetch_listings(limit=limit)
    except NotImplementedError as exc:
        raise HTTPException(status.HTTP_501_NOT_IMPLEMENTED, str(exc)) from exc

    summary = await ingest(db, admin.dealership_id, listings)
    summary["connector"] = name
    summary["source"] = connector.source
    await audit.record(db, actor=admin, action=AuditAction.SETTINGS_CHANGED, entity="connector",
                       entity_id=None, new_value=summary)
    return summary
