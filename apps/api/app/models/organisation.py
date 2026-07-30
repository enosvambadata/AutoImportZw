"""Dealership, users and refresh tokens."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, IntPKMixin, TimestampMixin


class Dealership(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "dealerships"

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    trading_name: Mapped[str | None] = mapped_column(String(200))
    company_number: Mapped[str | None] = mapped_column(String(20))
    vat_registered: Mapped[bool] = mapped_column(Boolean, default=False)
    vat_number: Mapped[str | None] = mapped_column(String(20))
    postcode: Mapped[str | None] = mapped_column(String(12))
    default_currency: Mapped[str] = mapped_column(String(3), default="GBP")
    default_target_profit: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("1200"))
    default_risk_reserve: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("300"))
    mandatory_min_risk_reserve: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("150"))
    default_min_roi: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.15"))
    default_vat_treatment: Mapped[str] = mapped_column(String(20), default="MARGIN")
    vat_rate: Mapped[Decimal] = mapped_column(Numeric(6, 4), default=Decimal("0.20"))
    max_acceptable_pessimistic_loss: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), default=Decimal("-500"))
    allow_category_n: Mapped[bool] = mapped_column(Boolean, default=True)
    allow_category_s: Mapped[bool] = mapped_column(Boolean, default=False)
    risk_weights: Mapped[dict] = mapped_column(JSON, default=dict)

    users: Mapped[list[User]] = relationship(back_populates="dealership")


class User(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "users"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    first_name: Mapped[str] = mapped_column(String(80))
    last_name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="VIEWER")
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    dealership: Mapped[Dealership] = relationship(back_populates="users")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class RefreshToken(Base, IntPKMixin, TimestampMixin):
    """Server-side record of an issued refresh token (hashed), for rotation & revocation."""

    __tablename__ = "refresh_tokens"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
