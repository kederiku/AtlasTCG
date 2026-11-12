"""Localized sets and versioned normalized card documents.

Existing observations stay at version 0 until the explicit offline backfill.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    document = sa.JSON().with_variant(JSONB(), "postgresql")
    localized_sets = op.create_table(
        "localized_sets",
        sa.Column("game", sa.String(), primary_key=True),
        sa.Column("source", sa.String(), primary_key=True),
        sa.Column("source_id", sa.String(), primary_key=True),
        sa.Column("language", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("release_date", sa.Date(), nullable=True),
        sa.Column("info", document, nullable=False),
    )
    bind = op.get_bind()
    old_cards = sa.Table("cards", sa.MetaData(), autoload_with=bind)
    # Bounded scan of identities, then one insert per distinct set/language.
    identities = bind.execute(
        sa.select(
            old_cards.c.game, old_cards.c.source, old_cards.c.set_id, old_cards.c.language
        ).distinct()
    ).mappings()
    for row in identities:
        bind.execute(
            localized_sets.insert().values(
                game=row["game"],
                source=row["source"],
                source_id=row["set_id"],
                language=row["language"],
                name=None,
                info={},
            )
        )
    with op.batch_alter_table("cards") as batch:
        batch.add_column(sa.Column("rarity", sa.String(), nullable=True))
        for name in ("illustrators", "faces"):
            batch.add_column(sa.Column(name, document, nullable=False, server_default="[]"))
        for name in ("legalities", "game_data"):
            batch.add_column(sa.Column(name, document, nullable=False, server_default="{}"))
        batch.add_column(
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="0")
        )
        batch.create_foreign_key(
            "fk_cards_localized_set",
            "localized_sets",
            ["game", "source", "set_id", "language"],
            ["game", "source", "source_id", "language"],
        )
        batch.create_index("ix_cards_set_identity", ["game", "source", "set_id", "language"])


def downgrade():
    with op.batch_alter_table("cards") as batch:
        batch.drop_constraint("fk_cards_localized_set", type_="foreignkey")
        batch.drop_index("ix_cards_set_identity")
        for name in (
            "rarity",
            "illustrators",
            "faces",
            "legalities",
            "game_data",
            "schema_version",
        ):
            batch.drop_column(name)
    op.drop_table("localized_sets")
