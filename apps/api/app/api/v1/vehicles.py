"""Vehicles and vehicle history."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.deps import CurrentUser, require_buyer
from ...db.session import get_db
from ...models.appraisal import Appraisal
from ...models.catalogue import Vehicle, VehicleHistory
from ...models.organisation import User
from ...schemas.catalogue import (
    VehicleCreate,
    VehicleHistoryBase,
    VehicleHistoryOut,
    VehicleOut,
    VehicleUpdate,
)
from ...schemas.common import Page
from ...services.appraisal_service import compute_and_store
from ...services.enrichment import enrich_vehicle

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("", response_model=Page[VehicleOut])
async def list_vehicles(
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
    q: str | None = None,
    make: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
):
    stmt = select(Vehicle).where(Vehicle.dealership_id == user.dealership_id)
    if make:
        stmt = stmt.where(Vehicle.make == make)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(Vehicle.registration.ilike(like), Vehicle.make.ilike(like),
                             Vehicle.model.ilike(like), Vehicle.vin.ilike(like)))
    total = (await db.execute(select(func.count()).select_from(stmt.subquery()))).scalar_one()
    rows = (await db.execute(
        stmt.options(selectinload(Vehicle.history)).order_by(Vehicle.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    )).scalars().all()
    return Page(items=rows, total=total, page=page, page_size=page_size)


@router.get("/{vehicle_id}", response_model=VehicleOut)
async def get_vehicle(vehicle_id: int, user: CurrentUser,
                     db: Annotated[AsyncSession, Depends(get_db)]):
    vehicle = (await db.execute(
        select(Vehicle).options(selectinload(Vehicle.history))
        .where(Vehicle.id == vehicle_id, Vehicle.dealership_id == user.dealership_id)
    )).scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    return vehicle


@router.post("", response_model=VehicleOut, status_code=status.HTTP_201_CREATED)
async def create_vehicle(
    payload: VehicleCreate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    data = payload.model_dump(exclude={"history"})
    vehicle = Vehicle(dealership_id=buyer.dealership_id, **data)
    if payload.history:
        vehicle.history = VehicleHistory(
            **payload.history.model_dump(),
            data_retrieved_at=datetime.now(timezone.utc),
        )
    db.add(vehicle)
    await db.flush()
    await db.refresh(vehicle, attribute_names=["history"])
    return vehicle


@router.patch("/{vehicle_id}", response_model=VehicleOut)
async def update_vehicle(
    vehicle_id: int,
    payload: VehicleUpdate,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    vehicle = await db.get(Vehicle, vehicle_id)
    if vehicle is None or vehicle.dealership_id != buyer.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(vehicle, key, value)
    await db.flush()
    await db.refresh(vehicle, attribute_names=["history"])
    return vehicle


@router.post("/{vehicle_id}/enrich", response_model=VehicleOut)
async def enrich(
    vehicle_id: int,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    force: bool = False,
):
    """Look up the registration and apply identity + MOT + history, then recompute appraisals."""
    vehicle = (await db.execute(
        select(Vehicle).options(selectinload(Vehicle.history))
        .where(Vehicle.id == vehicle_id, Vehicle.dealership_id == buyer.dealership_id)
    )).scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    if not vehicle.registration:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "This vehicle has no registration to look up")

    enrich_vehicle(vehicle, force=force)
    await db.flush()

    # Recompute appraisals for this vehicle so the refreshed MOT/history feeds their risk.
    appraisals = (await db.execute(
        select(Appraisal).options(
            selectinload(Appraisal.cost_items), selectinload(Appraisal.comparables))
        .where(Appraisal.vehicle_id == vehicle.id,
               Appraisal.dealership_id == buyer.dealership_id)
    )).scalars().all()
    for appraisal in appraisals:
        await compute_and_store(db, appraisal)
    await db.flush()
    await db.refresh(vehicle, attribute_names=["history"])
    return vehicle


@router.put("/{vehicle_id}/history", response_model=VehicleHistoryOut)
async def upsert_history(
    vehicle_id: int,
    payload: VehicleHistoryBase,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    vehicle = (await db.execute(
        select(Vehicle).options(selectinload(Vehicle.history))
        .where(Vehicle.id == vehicle_id, Vehicle.dealership_id == buyer.dealership_id)
    )).scalar_one_or_none()
    if vehicle is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Vehicle not found")
    if vehicle.history is None:
        vehicle.history = VehicleHistory(vehicle_id=vehicle.id)
    for key, value in payload.model_dump().items():
        setattr(vehicle.history, key, value)
    vehicle.history.data_retrieved_at = datetime.now(timezone.utc)
    await db.flush()
    return vehicle.history
