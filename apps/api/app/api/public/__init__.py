"""Public, unauthenticated storefront API (mounted at /api/public).

Only ever exposes cars deliberately published to the storefront and accepts buyer enquiries/briefs.
Never returns internal bid ceilings, margins or admin data.
"""

from fastapi import APIRouter

from . import storefront

public_router = APIRouter(prefix="/api/public")
public_router.include_router(storefront.router)
