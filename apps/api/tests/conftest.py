"""Pytest fixtures for API integration tests (in-memory SQLite, dependency-overridden)."""

from __future__ import annotations

from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.security import hash_password
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.catalogue import AuctionFeeBand, AuctionHouse
from app.models.organisation import Dealership, User

TEST_URL = "sqlite+aiosqlite://"


@pytest_asyncio.fixture
async def engine():
    eng = create_async_engine(TEST_URL, connect_args={"check_same_thread": False},
                              poolclass=StaticPool)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)


@pytest_asyncio.fixture
async def seeded(session_factory):
    """Create a dealership, three users (one per role) and an auction house with fee bands."""
    async with session_factory() as s:
        dealership = Dealership(name="Test Motors", vat_rate=Decimal("0.20"),
                                mandatory_min_risk_reserve=Decimal("150"),
                                max_acceptable_pessimistic_loss=Decimal("-500"),
                                allow_category_n=True, allow_category_s=False, risk_weights={})
        s.add(dealership)
        await s.flush()
        pw = hash_password("Password123!")
        users = {
            "admin": User(dealership_id=dealership.id, first_name="Ad", last_name="Min",
                          email="admin@example.com", password_hash=pw, role="ADMIN"),
            "buyer": User(dealership_id=dealership.id, first_name="Bu", last_name="Yer",
                          email="buyer@example.com", password_hash=pw, role="BUYER"),
            "viewer": User(dealership_id=dealership.id, first_name="Vi", last_name="Ewer",
                           email="viewer@example.com", password_hash=pw, role="VIEWER"),
        }
        s.add_all(list(users.values()))
        house = AuctionHouse(dealership_id=dealership.id, name="Test Auctions",
                             fee_calc_type="PERCENTAGE")
        house.fee_bands = [AuctionFeeBand(percentage=Decimal("0.08"), minimum_fee=Decimal("180"),
                                          vat_applicable=True)]
        s.add(house)
        await s.commit()
        return {"dealership_id": dealership.id, "house_id": house.id}


@pytest_asyncio.fixture
async def client(engine, session_factory):
    # Reset the in-process auth rate-limit bucket so tests don't leak state into each other.
    from app.core import ratelimit
    ratelimit._buckets.clear()

    async def override_get_db():
        async with session_factory() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.clear()


async def login(client: AsyncClient, email: str, password: str = "Password123!") -> str:
    resp = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
