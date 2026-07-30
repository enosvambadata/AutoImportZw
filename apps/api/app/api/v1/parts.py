"""Parts sourcing from eBay for damaged panels (photo damage scan → replacement parts)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.deps import require_buyer
from ...db.session import get_db
from ...integrations import get_parts_provider
from ...models.appraisal import Appraisal, CostItem
from ...models.catalogue import Vehicle
from ...models.enums import AuditAction
from ...models.organisation import User
from ...services import audit
from ...services.appraisal_service import compute_and_store

router = APIRouter(prefix="/parts", tags=["parts"])


def _category_for(panel: str) -> str:
    p = panel.lower()
    if any(w in p for w in ("wheel", "tyre", "tire", "alloy")):
        return "TYRES"
    if any(w in p for w in ("glass", "screen", "window", "windscreen")):
        return "GLASS"
    if any(w in p for w in ("engine", "gearbox", "mechanic", "clutch", "turbo")):
        return "MECHANICAL"
    return "BODYWORK"


class PartsRequest(BaseModel):
    panels: list[str] = Field(default_factory=list, max_length=6)
    appraisal_id: int | None = None
    make: str | None = None
    model: str | None = None
    model_year: int | None = None
    limit: int = Field(default=3, ge=1, le=6)


@router.post("/for-damage")
async def parts_for_damage(
    payload: PartsRequest,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Search eBay for replacement parts for the given damaged panels."""
    make, model, year = payload.make, payload.model, payload.model_year
    if payload.appraisal_id is not None:
        appraisal = (await db.execute(
            select(Appraisal).where(Appraisal.id == payload.appraisal_id,
                                    Appraisal.dealership_id == buyer.dealership_id)
        )).scalar_one_or_none()
        if appraisal is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Appraisal not found")
        vehicle = await db.get(Vehicle, appraisal.vehicle_id)
        if vehicle:
            make = make or vehicle.make
            model = model or vehicle.model
            year = year or vehicle.model_year

    panels = list(dict.fromkeys(p.strip() for p in payload.panels if p.strip()))[:4]
    if not panels:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No panels supplied")

    provider = get_parts_provider()
    groups = []
    for panel in panels:
        query = " ".join(str(x) for x in (make, model, year, panel) if x)
        groups.append({
            "panel": panel,
            "query": query,
            "items": provider.search(query, limit=payload.limit),
        })

    # Report what actually served the results (eBay can fall back to mock if the keyset is disabled).
    served_live = any(it.get("source") == "EBAY" for g in groups for it in g["items"])

    return {
        "provider": "EBAY" if served_live else "MOCK_ADAPTER",
        "groups": groups,
        "disclaimer": ("Indicative used-part prices from eBay search — confirm fitment and condition "
                       "before buying."),
    }


class AttachPartsRequest(BaseModel):
    panels: list[str] = Field(default_factory=list, max_length=6)


@router.post("/attach/{appraisal_id}")
async def attach_parts(
    appraisal_id: int,
    payload: AttachPartsRequest,
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Add the cheapest eBay part per damaged panel as a cost item, then recompute the appraisal."""
    appraisal = (await db.execute(
        select(Appraisal).options(selectinload(Appraisal.cost_items),
                                  selectinload(Appraisal.comparables))
        .where(Appraisal.id == appraisal_id, Appraisal.dealership_id == buyer.dealership_id)
    )).scalar_one_or_none()
    if appraisal is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Appraisal not found")

    panels = list(dict.fromkeys(p.strip() for p in payload.panels if p.strip()))[:4]
    if not panels:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "No panels supplied")

    vehicle = await db.get(Vehicle, appraisal.vehicle_id)
    provider = get_parts_provider()
    added = []
    served_live = False
    for panel in panels:
        query = " ".join(str(x) for x in
                         ((vehicle.make if vehicle else None),
                          (vehicle.model if vehicle else None),
                          (vehicle.model_year if vehicle else None), panel) if x)
        items = [it for it in provider.search(query, limit=5) if it.get("price") is not None]
        if not items:
            continue
        served_live = served_live or any(it.get("source") == "EBAY" for it in items)
        cheapest = min(items, key=lambda x: x["price"])
        dearest = max(it["price"] for it in items)
        appraisal.cost_items.append(CostItem(
            name=f"{panel} — part (eBay)"[:120],
            category=_category_for(panel),
            estimated_amount=cheapest["price"],
            minimum_amount=cheapest["price"],
            maximum_amount=dearest,
            certainty="MEDIUM",
            notes=(f"Cheapest eBay match: {cheapest.get('title', '')}")[:250],
        ))
        added.append({"panel": panel, "cheapest": cheapest["price"], "dearest": dearest,
                      "title": cheapest.get("title")})

    if not added:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "No priced parts found for those panels")

    await db.flush()
    result = await compute_and_store(db, appraisal)
    await audit.record(db, actor=buyer, action=AuditAction.COST_CHANGED, entity="appraisal",
                       entity_id=appraisal.id,
                       new_value={"source": "EBAY" if served_live else "MOCK_ADAPTER",
                                  "parts_added": len(added)})
    calc = result.get("calculation") or {}
    return {
        "provider": "EBAY" if served_live else "MOCK_ADAPTER",
        "added": added,
        "recommendation": result["recommendation"]["decision"],
        "expected_profit": calc.get("expected_profit"),
        "safe_max_bid": calc.get("safe_max_bid"),
        "absolute_max_bid": calc.get("absolute_max_bid"),
    }
