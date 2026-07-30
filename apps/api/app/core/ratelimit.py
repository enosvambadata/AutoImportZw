"""Minimal in-process fixed-window rate limiter for auth endpoints.

For production, replace with a Redis-backed limiter (documented in docs/SECURITY.md). This
implementation is process-local and adequate for a single-instance MVP.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import HTTPException, Request, status

from .config import settings

_buckets: dict[str, list[float]] = defaultdict(list)


def _enforce(request: Request, limit: int, scope: str, message: str) -> None:
    key = f"{request.client.host if request.client else 'unknown'}:{scope}"
    now = time.time()
    window_start = now - 60
    hits = [t for t in _buckets[key] if t > window_start]
    if len(hits) >= limit:
        raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, message)
    hits.append(now)
    _buckets[key] = hits


def rate_limit_auth(request: Request) -> None:
    _enforce(request, settings.auth_rate_limit_per_minute, f"auth:{request.url.path}",
             "Too many attempts. Please wait a minute and try again.")


def rate_limit_public_write(request: Request) -> None:
    """Throttle unauthenticated form submissions (enquiries, briefs, vet requests)."""
    _enforce(request, settings.public_write_rate_limit_per_minute, "public_write",
             "Too many submissions. Please wait a minute and try again.")


def rate_limit_mot_check(request: Request) -> None:
    """Throttle the public MOT lookup so it can't drain the DVSA quota."""
    _enforce(request, settings.mot_check_rate_limit_per_minute, "mot_check",
             "Too many lookups. Please wait a minute and try again.")
