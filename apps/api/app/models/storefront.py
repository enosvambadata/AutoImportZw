"""Import-concierge storefront: published candidate cars, buyer enquiries and sourcing briefs.

A SaleListing is a car we've appraised and chosen to publish publicly as a sourcing candidate (we do
NOT hold stock — the buyer commits and deposits, then we buy on their behalf). The public site reads
only PUBLISHED/RESERVED listings; internal bid ceilings and margins are never exposed.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from sqlalchemy import JSON, DateTime, ForeignKey, Numeric, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..db.base import Base, IntPKMixin, TimestampMixin

# Landed-cost components summed to the buyer-facing delivered price.
_LANDED_PARTS = (
    "vehicle_price", "auction_fees", "uk_transport", "ocean_freight",
    "import_duty", "import_surtax", "import_vat", "inland_transport",
    "estimated_repairs", "service_fee",
)


class SaleListing(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "sale_listings"

    dealership_id: Mapped[int] = mapped_column(ForeignKey("dealerships.id"), index=True)
    vehicle_id: Mapped[int] = mapped_column(ForeignKey("vehicles.id"), index=True)
    appraisal_id: Mapped[int | None] = mapped_column(ForeignKey("appraisals.id"))

    slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    # DRAFT / PUBLISHED / RESERVED / SOURCING / SHIPPED / DELIVERED / WITHDRAWN
    headline: Mapped[str] = mapped_column(String(200))
    blurb: Mapped[str | None] = mapped_column(Text)
    video_url: Mapped[str | None] = mapped_column(String(500))
    image_urls: Mapped[list | None] = mapped_column(
        JSON, default=list, server_default=text("'[]'"))  # gallery photo URLs
    currency: Mapped[str] = mapped_column(String(3), default="USD")

    # Landed-cost breakdown (buyer-facing, delivered to destination).
    vehicle_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    auction_fees: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    uk_transport: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    ocean_freight: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    import_duty: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))  # customs duty
    import_surtax: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    import_vat: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    inland_transport: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    estimated_repairs: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))
    service_fee: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=Decimal("0"))

    dest_country: Mapped[str] = mapped_column(String(60), default="Zimbabwe")
    dest_port: Mapped[str | None] = mapped_column(String(60))
    dest_city: Mapped[str | None] = mapped_column(String(60))

    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    vehicle: Mapped["Vehicle"] = relationship()  # noqa: F821, UP037
    enquiries: Mapped[list["Enquiry"]] = relationship(  # noqa: UP037
        back_populates="sale_listing", cascade="all, delete-orphan")

    @property
    def landed_total(self) -> Decimal:
        return sum((getattr(self, p) or Decimal("0")) for p in _LANDED_PARTS)


class Enquiry(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "enquiries"

    dealership_id: Mapped[int | None] = mapped_column(ForeignKey("dealerships.id"), index=True)
    sale_listing_id: Mapped[int | None] = mapped_column(ForeignKey("sale_listings.id"), index=True)

    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str] = mapped_column(String(200))  # phone / WhatsApp / email
    message: Mapped[str | None] = mapped_column(Text)
    deposit_amount: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    deposit_status: Mapped[str] = mapped_column(String(20), default="NONE")  # NONE/PENDING/PAID
    status: Mapped[str] = mapped_column(String(20), default="NEW")  # NEW/CONTACTED/RESERVED/CLOSED

    sale_listing: Mapped[SaleListing | None] = relationship(back_populates="enquiries")


class BuyerBrief(Base, IntPKMixin, TimestampMixin):
    __tablename__ = "buyer_briefs"

    dealership_id: Mapped[int | None] = mapped_column(ForeignKey("dealerships.id"), index=True)
    name: Mapped[str] = mapped_column(String(120))
    contact: Mapped[str] = mapped_column(String(200))
    make: Mapped[str | None] = mapped_column(String(60))
    model: Mapped[str | None] = mapped_column(String(80))
    budget_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 2))
    source_url: Mapped[str | None] = mapped_column(String(500))  # a link to vet, if the buyer found one
    notes: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="NEW")
