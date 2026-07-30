"""Dealership data-isolation tests."""

from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.security import hash_password
from app.models.catalogue import Vehicle
from app.models.organisation import Dealership, User

from .conftest import auth_header, login

pytestmark = pytest.mark.asyncio


async def test_user_cannot_see_other_dealership_vehicle(client, seeded, engine):
    # Create a second dealership with its own buyer and a vehicle.
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        other = Dealership(name="Rival Cars", risk_weights={})
        s.add(other)
        await s.flush()
        s.add(User(dealership_id=other.id, first_name="R", last_name="V",
                   email="rival@example.com", password_hash=hash_password("Password123!"),
                   role="BUYER"))
        s.add(Vehicle(dealership_id=other.id, make="Rival", model="Secret"))
        await s.commit()

    # A user from the first dealership must not see the rival's vehicle in their list.
    token = await login(client, "buyer@example.com")
    resp = await client.get("/api/v1/vehicles", headers=auth_header(token))
    assert resp.status_code == 200
    makes = [v["make"] for v in resp.json()["items"]]
    assert "Rival" not in makes


async def test_direct_fetch_of_foreign_vehicle_is_404(client, seeded, engine):
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as s:
        other = Dealership(name="Rival Cars", risk_weights={})
        s.add(other)
        await s.flush()
        vehicle = Vehicle(dealership_id=other.id, make="Rival", model="Secret")
        s.add(vehicle)
        await s.commit()
        foreign_id = vehicle.id

    token = await login(client, "buyer@example.com")
    resp = await client.get(f"/api/v1/vehicles/{foreign_id}", headers=auth_header(token))
    assert resp.status_code == 404
