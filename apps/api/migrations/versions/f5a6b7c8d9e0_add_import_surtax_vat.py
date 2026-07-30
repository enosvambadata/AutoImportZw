"""add sale_listings.import_surtax and import_vat (ZIMRA duty breakdown)

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-07-30

"""

import sqlalchemy as sa
from alembic import op

revision: str = "f5a6b7c8d9e0"
down_revision: str | None = "e4f5a6b7c8d9"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(12, 2)


def upgrade() -> None:
    op.add_column("sale_listings", sa.Column("import_surtax", _MONEY, nullable=False, server_default="0"))
    op.add_column("sale_listings", sa.Column("import_vat", _MONEY, nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("sale_listings", "import_vat")
    op.drop_column("sale_listings", "import_surtax")
