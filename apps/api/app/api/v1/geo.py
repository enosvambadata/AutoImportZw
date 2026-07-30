"""Distance / transport helpers backed by postcodes.io (free)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import CurrentUser
from ...db.session import get_db
from ...integrations import geo
from ...models.catalogue import AuctionHouse
from ...models.organisation import Dealership

router = APIRouter(prefix="/geo", tags=["geo"])


@router.get("/distance")
async def distance(user: CurrentUser, origin: str = Query(min_length=2),
                  destination: str = Query(min_length=2)):
    miles = geo.distance_between(origin, destination)
    if miles is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "Could not resolve one or both postcodes")
    return {"origin": origin, "destination": destination, "miles": miles,
            "estimated_transport": geo.estimate_transport(miles)}


@router.get("/auction-transport/{auction_house_id}")
async def auction_transport(
    auction_house_id: int,
    user: CurrentUser,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Distance from the dealership to an auction house, with a rough transport estimate."""
    house = await db.get(AuctionHouse, auction_house_id)
    if house is None or house.dealership_id != user.dealership_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Auction house not found")
    dealership = await db.get(Dealership, user.dealership_id)
    if not dealership.postcode or not house.postcode:
        return {"miles": None, "estimated_transport": None,
                "note": "Set both your dealership postcode and this auction house's postcode."}
    miles = geo.distance_between(dealership.postcode, house.postcode)
    if miles is None:
        return {"miles": None, "estimated_transport": None,
                "note": "Could not resolve one or both postcodes."}
    return {"miles": miles, "estimated_transport": geo.estimate_transport(miles),
            "from": dealership.postcode, "to": house.postcode}
