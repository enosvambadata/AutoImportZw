"""API v1 router aggregation."""

from fastapi import APIRouter

from . import (
    analytics,
    appraisals,
    auction_houses,
    audit,
    auth,
    connectors,
    csv_import,
    dealership,
    geo,
    listings,
    lookups,
    media,
    parts,
    purchases,
    sales,
    shortlist,
    storefront,
    users,
    vehicles,
    vision,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(dealership.router)
api_router.include_router(auction_houses.router)
api_router.include_router(connectors.router)
api_router.include_router(vehicles.router)
api_router.include_router(listings.router)
api_router.include_router(lookups.router)
api_router.include_router(geo.router)
api_router.include_router(media.router)
api_router.include_router(parts.router)
api_router.include_router(csv_import.router)
api_router.include_router(appraisals.router)
api_router.include_router(purchases.router)
api_router.include_router(sales.router)
api_router.include_router(shortlist.router)
api_router.include_router(storefront.router)
api_router.include_router(vision.router)
api_router.include_router(analytics.router)
api_router.include_router(audit.router)
