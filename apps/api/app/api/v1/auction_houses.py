"""Auction houses and their configurable fee bands (admin write)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.deps import CurrentUser, require_admin
from ...db.session import get_db
from ...models.catalogue import AuctionFeeBand, AuctionHouse
from ...models.organisation import User
from ...schemas.catalogue import (
    AuctionHouseCreate,
    AuctionHouseOut,
    AuctionHouseUpdate,
    FeeBandCreate,
    FeeBandOut,
)

router = APIRouter(prefix="/auction-houses", tags=["auction-houses"])


async def _get_owned(db: AsyncSession, house_id: int, dealership_id: int) -> AuctionHouse:
    house = (await db.execute(
        select(AuctionHouse).options(selectinload(AuctionHouse.fee_bands))
        .where(AuctionHouse.id == house_id, AuctionHouse.dealership_id == dealership_id)
    )).scalar_one_or_none()
    if house is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Auction house not found")
    return house


@router.get("", response_model=list[AuctionHouseOut])
async def list_houses(user: CurrentUser, db: Annotated[AsyncSession, Depends(get_db)]):
    rows = (await db.execute(
        select(AuctionHouse).options(selectinload(AuctionHouse.fee_bands))
        .where(AuctionHouse.dealership_id == user.dealership_id).order_by(AuctionHouse.name)
    )).scalars().all()
    return rows


@router.post("", response_model=AuctionHouseOut, status_code=status.HTTP_201_CREATED)
async def create_house(
    payload: AuctionHouseCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    house = AuctionHouse(
        dealership_id=admin.dealership_id,
        **payload.model_dump(exclude={"fee_bands"}),
    )
    for band in payload.fee_bands:
        house.fee_bands.append(AuctionFeeBand(**band.model_dump()))
    db.add(house)
    await db.flush()
    await db.refresh(house, attribute_names=["fee_bands"])
    return house


@router.patch("/{house_id}", response_model=AuctionHouseOut)
async def update_house(
    house_id: int,
    payload: AuctionHouseUpdate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    house = await _get_owned(db, house_id, admin.dealership_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(house, key, value)
    await db.flush()
    return house


@router.post("/{house_id}/fee-bands", response_model=FeeBandOut,
             status_code=status.HTTP_201_CREATED)
async def add_fee_band(
    house_id: int,
    payload: FeeBandCreate,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    house = await _get_owned(db, house_id, admin.dealership_id)
    band = AuctionFeeBand(auction_house_id=house.id, **payload.model_dump())
    db.add(band)
    await db.flush()
    return band


@router.delete("/{house_id}/fee-bands/{band_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fee_band(
    house_id: int,
    band_id: int,
    admin: Annotated[User, Depends(require_admin)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    await _get_owned(db, house_id, admin.dealership_id)
    band = await db.get(AuctionFeeBand, band_id)
    if band is None or band.auction_house_id != house_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Fee band not found")
    await db.delete(band)
