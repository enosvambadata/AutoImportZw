"""Dealership settings schemas."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field

from .common import ORMModel


class DealershipOut(ORMModel):
    id: int
    name: str
    trading_name: str | None
    company_number: str | None
    vat_registered: bool
    vat_number: str | None
    postcode: str | None
    default_currency: str
    default_target_profit: Decimal
    default_risk_reserve: Decimal
    mandatory_min_risk_reserve: Decimal
    default_min_roi: Decimal
    default_vat_treatment: str
    vat_rate: Decimal
    max_acceptable_pessimistic_loss: Decimal
    allow_category_n: bool
    allow_category_s: bool
    risk_weights: dict


class DealershipUpdate(BaseModel):
    name: str | None = None
    trading_name: str | None = None
    company_number: str | None = None
    vat_registered: bool | None = None
    vat_number: str | None = None
    postcode: str | None = None
    default_target_profit: Decimal | None = Field(default=None, ge=0)
    default_risk_reserve: Decimal | None = Field(default=None, ge=0)
    mandatory_min_risk_reserve: Decimal | None = Field(default=None, ge=0)
    default_min_roi: Decimal | None = Field(default=None, ge=0, le=5)
    default_vat_treatment: str | None = None
    vat_rate: Decimal | None = Field(default=None, ge=0, le=1)
    max_acceptable_pessimistic_loss: Decimal | None = None
    allow_category_n: bool | None = None
    allow_category_s: bool | None = None
    risk_weights: dict | None = None
