"""add storefront tables (sale_listings, enquiries, buyer_briefs)

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-07-30

"""

import sqlalchemy as sa
from alembic import op

revision: str = "d3e4f5a6b7c8"
down_revision: str | None = "c2d3e4f5a6b7"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(12, 2)


def upgrade() -> None:
    op.create_table(
        "sale_listings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dealership_id", sa.Integer(), sa.ForeignKey("dealerships.id"), nullable=False),
        sa.Column("vehicle_id", sa.Integer(), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("appraisal_id", sa.Integer(), sa.ForeignKey("appraisals.id"), nullable=True),
        sa.Column("slug", sa.String(160), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        sa.Column("headline", sa.String(200), nullable=False),
        sa.Column("blurb", sa.Text(), nullable=True),
        sa.Column("video_url", sa.String(500), nullable=True),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("vehicle_price", _MONEY, nullable=False, server_default="0"),
        sa.Column("auction_fees", _MONEY, nullable=False, server_default="0"),
        sa.Column("uk_transport", _MONEY, nullable=False, server_default="0"),
        sa.Column("ocean_freight", _MONEY, nullable=False, server_default="0"),
        sa.Column("import_duty", _MONEY, nullable=False, server_default="0"),
        sa.Column("inland_transport", _MONEY, nullable=False, server_default="0"),
        sa.Column("estimated_repairs", _MONEY, nullable=False, server_default="0"),
        sa.Column("service_fee", _MONEY, nullable=False, server_default="0"),
        sa.Column("dest_country", sa.String(60), nullable=False, server_default="Zimbabwe"),
        sa.Column("dest_port", sa.String(60), nullable=True),
        sa.Column("dest_city", sa.String(60), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sold_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sale_listings_slug", "sale_listings", ["slug"], unique=True)
    op.create_index("ix_sale_listings_dealership_id", "sale_listings", ["dealership_id"])
    op.create_index("ix_sale_listings_vehicle_id", "sale_listings", ["vehicle_id"])

    op.create_table(
        "enquiries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dealership_id", sa.Integer(), sa.ForeignKey("dealerships.id"), nullable=True),
        sa.Column("sale_listing_id", sa.Integer(), sa.ForeignKey("sale_listings.id"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("contact", sa.String(200), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("deposit_amount", _MONEY, nullable=True),
        sa.Column("deposit_status", sa.String(20), nullable=False, server_default="NONE"),
        sa.Column("status", sa.String(20), nullable=False, server_default="NEW"),
    )
    op.create_index("ix_enquiries_dealership_id", "enquiries", ["dealership_id"])
    op.create_index("ix_enquiries_sale_listing_id", "enquiries", ["sale_listing_id"])

    op.create_table(
        "buyer_briefs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("dealership_id", sa.Integer(), sa.ForeignKey("dealerships.id"), nullable=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("contact", sa.String(200), nullable=False),
        sa.Column("make", sa.String(60), nullable=True),
        sa.Column("model", sa.String(80), nullable=True),
        sa.Column("budget_usd", _MONEY, nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="NEW"),
    )
    op.create_index("ix_buyer_briefs_dealership_id", "buyer_briefs", ["dealership_id"])


def downgrade() -> None:
    op.drop_table("buyer_briefs")
    op.drop_table("enquiries")
    op.drop_table("sale_listings")
