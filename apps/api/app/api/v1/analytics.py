"""Dashboard and analytics endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import CurrentUser
from ...db.session import get_db
from ...services import analytics as analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/dashboard")
async def dashboard(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    return await analytics_service.dashboard(db, user.dealership_id)


@router.get("/performance")
async def performance(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    return await analytics_service.analytics(db, user.dealership_id)
