"""CSV catalogue import: template, validated preview, and commit into listings.

Intended for importing a dealer's **own account export** (e.g. a SYNETIQ catalogue download).
The commit step routes valid rows through the shared ingestion pipeline, so imported listings are
first-class and re-importing updates rather than duplicates.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import PlainTextResponse
from sqlalchemy.ext.asyncio import AsyncSession

from ...core.deps import CurrentUser, require_buyer
from ...db.session import get_db
from ...models.enums import AuditAction
from ...models.organisation import User
from ...services import audit, csv_import
from ...services.ingestion import ingest

router = APIRouter(prefix="/imports", tags=["imports"])


@router.get("/template", response_class=PlainTextResponse)
async def download_template(user: CurrentUser):
    return PlainTextResponse(
        csv_import.template_csv(),
        headers={"Content-Disposition": "attachment; filename=autobid_catalogue_template.csv"},
    )


@router.post("/preview")
async def preview_import(
    buyer: Annotated[User, Depends(require_buyer)],
    file: UploadFile = File(...),
    profile: str = Form("generic"),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please upload a .csv file")
    content = (await file.read()).decode("utf-8-sig", errors="replace")
    return csv_import.parse_and_validate(content, profile=profile)


@router.post("/commit")
async def commit_import(
    buyer: Annotated[User, Depends(require_buyer)],
    db: Annotated[AsyncSession, Depends(get_db)],
    file: UploadFile = File(...),
    profile: str = Form("generic"),
    auction_house: str | None = Form(None),
):
    """Import the valid rows of an uploaded CSV into this dealership's listings."""
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Please upload a .csv file")
    content = (await file.read()).decode("utf-8-sig", errors="replace")
    parsed = csv_import.parse_and_validate(content, profile=profile)
    listings = csv_import.to_normalized_listings(parsed, profile=profile,
                                                default_auction_house=auction_house or None)
    if not listings:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            "No importable rows (all rows had errors or were duplicates).")

    summary = await ingest(db, buyer.dealership_id, listings)
    summary["profile"] = profile
    summary["skipped_rows"] = parsed["summary"]["total"] - len(listings)
    await audit.record(db, actor=buyer, action=AuditAction.SETTINGS_CHANGED, entity="csv_import",
                       entity_id=None, new_value=summary)
    return summary
