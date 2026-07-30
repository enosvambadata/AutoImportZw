"""Scan-and-shortlist endpoint: rank catalogue cars worth bidding on."""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import CurrentUser
from ...db.session import get_db
from ...services import shortlist as shortlist_service

router = APIRouter(prefix="/shortlist", tags=["shortlist"])


@router.get("")
async def get_shortlist(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    due_today: bool = Query(False, description="Only cars whose auction is today"),
    due_on: date | None = Query(None, description="Only cars whose auction is on this date"),
    auction_house_id: int | None = None,
    include: str = Query("STRONG_BUY,BUY", description="Comma-separated decisions to shortlist"),
    limit: int = Query(25, ge=1, le=100),
):
    on = due_on
    if due_today and on is None:
        on = datetime.now(timezone.utc).date()
    accepted = {d.strip().upper() for d in include.split(",") if d.strip()}
    return await shortlist_service.scan(
        db, user.dealership_id, accepted=accepted, auction_house_id=auction_house_id,
        due_on=on, limit=limit,
    )
