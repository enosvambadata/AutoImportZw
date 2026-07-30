"""Photo damage analysis: upload vehicle photos, get an advisor assessment (Claude vision).

Falls back to a clearly-labelled mock adapter when no Anthropic API key is configured, so the
feature is demonstrable without credentials. Optionally attaches the suggested cost items to an
appraisal and recomputes it.
"""

from __future__ import annotations

import base64
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ...core.config import settings
from ...core.deps import require_buyer
from ...db.session import get_db
from ...integrations import get_damage_provider
from ...models.appraisal import Appraisal, CostItem
from ...models.catalogue import Vehicle
from ...models.enums import AuditAction
from ...models.organisation import Dealership, User
from ...services import audit
from ...services.appraisal_service import compute_and_store

router = APIRouter(prefix="/vision", tags=["vision"])

ALLOWED_MEDIA = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_IMAGES = 6
MAX_BYTES = 5 * 1024 * 1024  # 5 MB per image


@router.get("/status")
async def vision_status(user: Annotated[User, Depends(require_buyer)]):
    """Report which analyser is active so the UI can label provenance correctly."""
    return {
        "provider": "CLAUDE_VISION" if settings.claude_vision_enabled else "MOCK_ADAPTER",
        "model": settings.anthropic_model if settings.claude_vision_enabled else None,
        "live": settings.claude_vision_enabled,
        "note": ("Claude vision is analysing real photos." if settings.claude_vision_enabled
                 else "No Anthropic API key configured — using a labelled demonstration adapter."),
    }


@router.post("/damage")
async def analyse_damage(
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    files: list[UploadFile] = File(...),
    appraisal_id: int | None = Form(None),
    notes: str | None = Form(None),
    attach_costs: bool = Form(False),
):
    if not files:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Upload at least one photo")
    if len(files) > MAX_IMAGES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"Upload at most {MAX_IMAGES} photos")

    images: list[tuple[str, str]] = []
    for f in files:
        media = (f.content_type or "").lower()
        if media not in ALLOWED_MEDIA:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"Unsupported image type: {media or 'unknown'}")
        data = await f.read()
        if len(data) > MAX_BYTES:
            raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                                f"{f.filename} exceeds the 5 MB limit")
        images.append((media, base64.b64encode(data).decode("ascii")))

    # Build "your details" context from the dealership and (optionally) the appraised vehicle.
    dealership = await db.get(Dealership, buyer.dealership_id)
    context: dict = {"dealership_name": dealership.name if dealership else None, "notes": notes}

    appraisal: Appraisal | None = None
    if appraisal_id is not None:
        appraisal = (await db.execute(
            select(Appraisal).options(selectinload(Appraisal.cost_items),
                                      selectinload(Appraisal.comparables))
            .where(Appraisal.id == appraisal_id,
                   Appraisal.dealership_id == buyer.dealership_id)
        )).scalar_one_or_none()
        if appraisal is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Appraisal not found")
        vehicle = await db.get(Vehicle, appraisal.vehicle_id)
        if vehicle:
            context.update({
                "make": vehicle.make, "model": vehicle.model, "derivative": vehicle.derivative,
                "model_year": vehicle.model_year, "mileage": vehicle.mileage,
            })
        context["target_profit"] = str(appraisal.target_profit)

    analysis = get_damage_provider().analyse(images, context)

    attached = False
    if attach_costs and appraisal is not None:
        for c in analysis["result"].get("suggested_cost_items", []):
            appraisal.cost_items.append(CostItem(
                name=c.get("name", "Repair (from photo scan)")[:120],
                category=c.get("category", "BODYWORK"),
                estimated_amount=c.get("estimated_amount", 0),
                minimum_amount=c.get("minimum_amount"),
                maximum_amount=c.get("maximum_amount"),
                certainty="LOW",
                notes="Suggested by photo damage scan — verify before bidding.",
            ))
        await db.flush()
        await compute_and_store(db, appraisal)
        await audit.record(db, actor=buyer, action=AuditAction.COST_CHANGED, entity="appraisal",
                           entity_id=appraisal.id,
                           new_value={"source": analysis["analysis_source"],
                                      "added_costs": len(
                                          analysis["result"].get("suggested_cost_items", []))})
        attached = True

    analysis["costs_attached"] = attached
    return analysis
