"""add vehicle notes (seller description captured from listings)

Revision ID: b1c2d3e4f5a6
Revises: a790091bcfc8
Create Date: 2026-07-29

"""

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "a790091bcfc8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("vehicles", sa.Column("notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("vehicles", "notes")
