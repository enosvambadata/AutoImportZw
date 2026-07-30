"""add buyer_briefs.source_url (link a buyer wants us to vet)

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-30

"""

import sqlalchemy as sa
from alembic import op

revision: str = "a6b7c8d9e0f1"
down_revision: str | None = "f5a6b7c8d9e0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("buyer_briefs", sa.Column("source_url", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("buyer_briefs", "source_url")
