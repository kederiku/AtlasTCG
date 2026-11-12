"""Create localized source records."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cards",
        sa.Column("game", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), primary_key=True),
        sa.Column("language", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("set_id", sa.String(), nullable=False),
        sa.Column("number", sa.String(), nullable=False),
        sa.Column("source_url", sa.String(), nullable=False),
        sa.Column("image_urls", sa.JSON(), nullable=False),
        sa.Column("images", sa.JSON(), nullable=False),
        sa.Column("raw", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_cards_name", "cards", ["name"])
    op.create_index("ix_cards_set_id", "cards", ["set_id"])


def downgrade():
    op.drop_table("cards")
